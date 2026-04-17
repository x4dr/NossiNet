import logging
from Data import connect_db
from gamepack.WikiPage import WikiPage

log = logging.getLogger(__name__)


def sync_clocks_with_db():
    log.debug("Starting clock synchronization with database.")
    db = connect_db("sync_clocks")

    all_clocks = []
    root = WikiPage.wikipath()
    for md_file in WikiPage.wikindex():
        page_id = md_file.relative_to(root).as_posix()
        try:
            content = md_file.read_text()
            seen_on_page = set()
            for match in WikiPage.clock_re.finditer(content):
                name = match.group("name")
                if name in seen_on_page:
                    continue
                seen_on_page.add(name)
                current = int(match.group("current"))
                total = int(match.group("maximum"))
                all_clocks.append((page_id, name, current, total))
        except Exception as e:
            log.error(f"Error parsing clock in {md_file}: {e}")

    cursor = db.cursor()
    cursor.execute("BEGIN TRANSACTION")
    try:
        cursor.execute(
            "CREATE TEMP TABLE temp_clocks (page_id TEXT, clock_name TEXT, current_val INTEGER, total_val INTEGER)"
        )
        cursor.executemany("INSERT INTO temp_clocks VALUES (?, ?, ?, ?)", all_clocks)

        cursor.execute(
            """
            UPDATE clocks
            SET current_val = t.current_val, total_val = t.total_val
            FROM temp_clocks t
            WHERE clocks.page_id = t.page_id AND clocks.clock_name = t.clock_name
        """
        )

        cursor.execute(
            """
            INSERT INTO clocks (page_id, clock_name, current_val, total_val)
            SELECT t.page_id, t.clock_name, t.current_val, t.total_val
            FROM temp_clocks t
            LEFT JOIN clocks c ON t.page_id = c.page_id AND t.clock_name = c.clock_name
            WHERE c.clock_name IS NULL
        """
        )

        cursor.execute(
            """
            DELETE FROM clocks
            WHERE NOT EXISTS (
                SELECT 1 FROM temp_clocks t
                WHERE t.page_id = clocks.page_id AND t.clock_name = clocks.clock_name
            )
        """
        )

        cursor.execute("DROP TABLE temp_clocks")
        db.commit()
        log.debug("Clock synchronization completed.")
    except Exception as e:
        db.rollback()
        log.error(f"Clock synchronization failed: {e}")
        raise

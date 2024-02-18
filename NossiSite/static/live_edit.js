
window.addEventListener("load", () => {
        const csrf_token =  document.querySelector('meta[name="csrf-token"]').content;

        let lock_edit_content = false;
        window.get_edit_content =
            (con, ref) => {
                return async () => {
                    if (lock_edit_content) return;
                    lock_edit_content = true
                    const {category, section, item} = ref.dataset;
                    const response = await fetch("/live_edit", {
                        method: 'POST',
                        body: JSON.stringify({"context": con, "cat": category, "sec": section, "it":item}),
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrf_token
                        }
                    });

                    let reply;
                    try {
                        reply = await response.json(); //extract JSON from the http response
                    }
                    catch (e) {
                        reply = {"data":""}
                        alert("Internal Server Error!")
                    }
                    lock_edit_content = false;
                    if (reply["data"].length<1){
                        ref.className= ref.className.replace("editeable","failed")
                        ref.onclick=()=>{};
                    }
                    else {
                        console.log(reply)
                        if (reply["type"] === "table") {
                            table_row_overlay_edit(reply)
                        }
                        else {
                            overlay_edit(reply)
                        }
                    }
                }
            };


        function overlay_edit(reply) {
            const editfield = document.getElementById("editfield");
            const overlay = document.getElementById("overlay");
            const textdiv = editfield.querySelector("textarea");
            const olddata = editfield.querySelector("[name='original']");
            const closebutton = editfield.querySelector("[name='closebutton']");
            editfield.className="editfield"
            editfield.classList.add("activeedit");
            textdiv.value = reply["data"];
            olddata.value = reply["data"];
            textdiv.focus();
            textdiv.click();
            //document.body.style.overflow="hidden"
            overlay.style.visibility = "visible";
            closebutton.onclick = () => {
            document.body.style.overflow="auto"
            editfield.className="editfield"
            textdiv.value = ""
            olddata.value = ""
            overlay.style.visibility="hidden";
        }
        }
        function table_row_overlay_edit(reply) {
            const editfield = document.getElementById("table_editor");
            const overlay = document.getElementById("overlay");
            const table = editfield.querySelector("table");
            const closebutton = editfield.querySelector("[name='closebutton']");
            const olddata = editfield.querySelector("[name='original']");
            const headers = reply["data"]["headers"];
            const rows = reply["data"]["rows"];
            const style = reply["data"]["styles"];
            console.log(reply)
            olddata.value = reply["original"];
            let thead = document.createElement('thead');
            table.appendChild(thead);
            let tr = document.createElement('tr');
            thead.appendChild(tr);

            for (let i = 0; i < headers.length; i++) {
                let cell = document.createElement('th');
                cell.innerHTML = headers[i];
                tr.appendChild(cell);
            }

            let tbody = document.createElement('tbody');
            table.appendChild(tbody);

            for (let i = 0; i < rows.length; i++) {
                let row = document.createElement('tr');
                for (let prop in rows[i]) {
                    console.log(rows[i][prop])
                    let cell = document.createElement('td');
                    let input = document.createElement('input');
                    input.value = rows[i][prop];
                    input.className = "leet"
                    input.name = "table_"+i+"_"+prop;
                    cell.appendChild(input);
                    row.appendChild(cell);
                }
                tbody.appendChild(row);
            }
            editfield.classList.add("activeedit");
            overlay.style.visibility = "visible";
            closebutton.onclick = () => {
                document.body.style.overflow="auto"
                editfield.className="editfield_table"
                table.innerHTML = ""
                overlay.style.visibility="hidden";
            }
        }




        const anchors = document.getElementsByClassName('editeable');
        const context_elem = document.getElementById('context_element');
        if (context_elem!=null){
            const context = context_elem.innerHTML;
            context_elem.remove();
            for (let i = 0; i < anchors.length; i++) {
                let anchor = anchors[i];

                anchor.onclick = get_edit_content(context, anchor)
            }
        }

    }
);

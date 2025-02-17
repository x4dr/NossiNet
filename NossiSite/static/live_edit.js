
window.addEventListener("load", () => {
        const csrf_token =  document.querySelector('meta[name="csrf-token"]').content;

        let lock_edit_content = false;
        window.get_edit_content =
            (con, ref) => {

                return async () => {
                    if (lock_edit_content) return;
                    lock_edit_content = true
                    const path =(ref.dataset.path ?? "").split("|");
                    const percentage = ref.dataset.percentage || "";
                    let req = {"context": con, "path": path, "percentage": percentage}
                    req.type = ref.dataset["type"] || "text";
                    const response = await fetch("/live_edit", {
                        method: 'POST',
                        body: JSON.stringify(req),
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
                        ref.className= ref.className.replace("editable","failed")
                        ref.onclick=()=>{};
                    }
                    else {
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
            const olddata = editfield.querySelector("[id='original']");
            const closebutton = editfield.querySelector("[id='closebutton']");
            editfield.className="editfield"
            editfield.classList.add("activeedit");
            textdiv.value = reply["data"];
            olddata.value = reply["data"];
            textdiv.focus();
            textdiv.click();
            overlay.style.opacity="1";
            overlay.style.zIndex="1";
            closebutton.onclick = () => {
                document.body.style.overflow="auto"
                editfield.className="editfield"
                textdiv.value = ""
                olddata.value = ""
                overlay.style.opacity="0";
                overlay.style.zIndex="-1";
            }
        }
        function table_row_overlay_edit(reply, path) {
            const editfield = document.getElementById("table_editor");
            const overlay = document.getElementById("overlay");
            const table = editfield.querySelector("table");
            const addbutton = editfield.querySelector("[id='addtable_entry']");
            const closebutton = editfield.querySelector("[id='closebutton']");
            const headers = reply["data"]["headers"];
            const rows = reply["data"]["rows"];
            editfield.querySelector("[name='styles']").value = reply["data"]["styles"];
            editfield.querySelector("[name='path']").value = JSON.stringify(reply["path"]);

            let header_row = table.querySelector("thead tr");
            header_row.innerHTML = "";
            for (let i = 0; i < headers.length; i++) {
                let cell = document.createElement('th');
                let input = document.createElement('input');
                input.value = headers[i];
                input.className = "bright"
                input.style.padding= "5px";
                input.style.alignContent= "center";
                input.style.color= "#007000";
                input.name = "header_"+i;
                cell.appendChild(input);
                header_row.appendChild(cell);
            }
            let tbody = table.querySelector("tbody");
            tbody.innerHTML = "";
            for (let i = 0; i < rows.length; i++) {
                let row = document.createElement('tr');
                for (let prop in rows[i]) {
                    let cell = document.createElement('td');
                    let input = document.createElement('input');
                    input.value = rows[i][prop];
                    input.className = "dark"
                    input.name = "table_"+i+"_"+prop;
                    cell.appendChild(input);
                    row.appendChild(cell);
                }
                tbody.appendChild(row);
            }
            editfield.classList.add("activeedit");
            overlay.style.opacity="1";
            overlay.style.zIndex="1";
            closebutton.onclick = () => {
                document.body.style.overflow="auto"
                editfield.className="editfield_table"
                overlay.style.zIndex="-1";
                overlay.style.opacity="0";
            }
            addbutton.onclick = () => {
                let row = document.createElement('tr');
                for (let i = 0; i < headers.length; i++) {
                    let cell = document.createElement('td');
                    let input = document.createElement('input');
                    input.value = "";
                    input.className = "dark"
                    input.name = "table_"+rows.length+"_"+i;
                    cell.appendChild(input);
                    row.appendChild(cell);
                }
                rows.push(row);
                tbody.appendChild(row);
            }
        }




        const anchors = document.getElementsByClassName('editable');
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

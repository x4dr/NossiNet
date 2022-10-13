
window.addEventListener("load", () => {
        const textdiv = document.getElementById("text");
        const editfield = document.getElementById("editfield");
        const closebutton = document.getElementById("closebutton");
        const overlay = document.getElementById("overlay");
        const olddata = document.getElementById("original");
        let lock = false;
        window.get_edit_content =
            (con, ref) => {
                return async () => {
                    if (lock) return;
                    lock = true
                    const {category, section, item} = ref.dataset;
                    const response = await fetch("/live_edit", {
                        method: 'POST',
                        body: JSON.stringify({"context": con, "cat": category, "sec": section, "it":item}),
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });

                    let reply;
                    try {
                        editfield.className="editfield"
                        reply = await response.json(); //extract JSON from the http response
                        editfield.classList.add("activeedit");
                    }
                    catch (e) {
                        reply = {"data":""}
                        alert("Internal Server Error!")
                    }
                    lock = false;
                    if (reply["data"].length<1){
                        ref.className= ref.className.replace("editeable","failed")
                        ref.onclick=()=>{};
                        editfield.className="editfield"
                    }
                    else {
                        textdiv.value = reply["data"];
                        olddata.value = reply["data"];
                        textdiv.focus();
                        textdiv.click();
                        //document.body.style.overflow="hidden"
                        overlay.style.visibility = "visible";
                    }
                };
            }

        closebutton.onclick = () => {
            document.body.style.overflow="auto"
            editfield.className="editfield"
            textdiv.value = ""
            olddata.value = ""
            overlay.style.visibility="hidden";
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

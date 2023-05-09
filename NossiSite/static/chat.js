function chat_main() {
    let socket = io.connect(location.protocol+'//' + document.domain + ':' + location.port + '/chat');
    socket.on('message', function (msg) {
        let box = document.querySelector('#chatbox');
        let div =  document.createElement('div');
        div.innerHTML = msg.data;
        box.appendChild(div);
        box.scrollTop = box.scrollHeight;
    });

    function keepAlive() {
        socket.emit('keep_alive', {data: 'blip'})
    }

    setInterval(keepAlive, 5000);

    socket.on('status', function (msg) {
        document.getElementById('statusmessage').innerHTML = msg.status
    });

    socket.on('connect', function () {
        socket.emit('ClientServerEvent', {data: '/connection established'});
        document.querySelector('#message_data').focus();
    });
    socket.emit("event", {data: 'connected'});
    let prevCommand = [];
    let commandCount = 0;
    let keyCount = 0;



    document.querySelector('#messageform').addEventListener('submit', function (event) {
        event.preventDefault();
        let message_data = document.querySelector('#message_data').value;
        if (message_data !== '') {
            socket.emit('message', {data: message_data});
            commandCount++;
            keyCount = 0;
            prevCommand[commandCount] = message_data;
            document.getElementById('message_data').value = ''
        }
        return false;
    });


    document.onkeydown = function (event) {
        if (event.defaultPrevented) {
            return; // Do nothing if the event was already processed
        }
        let msgdata = document.querySelector('#message_data');
        let index;
        if (event.key === " ") {
            if (!msgdata.is(':focus')) {
                msgdata.focus();
                return false
            }

        }

        if (event.key === "ArrowUp") {
            keyCount++;
            msgdata.focus();
            if (typeof prevCommand[keyCount] !== "undefined") {
                index = prevCommand.length - keyCount;
                msgdata.val(prevCommand[index]);
            } else {
                keyCount = 1;
                index = prevCommand.length - keyCount;
                msgdata.val(prevCommand[index]);
            }
            return false;
        } else if (event.key === "ArrowDown") {
            keyCount--;
            msgdata.focus();
            if (typeof prevCommand[keyCount] !== "undefined") {
                index = prevCommand.length - keyCount;
                msgdata.val(prevCommand[index]);
                //  moveCursorToEnd(msgdata)
            } else {
                if (prevCommand[commandCount] !== msgdata.val() && msgdata.val() !== '') {
                    commandCount++;
                    keyCount = 0;
                    prevCommand[commandCount] = msgdata.val();
                }
                msgdata.val('')
            }
            return false;
        }
    }
}

if (document.readyState !== 'loading') {
    chat_main();
} else {
    console.log('document was not ready, place code here');
    document.addEventListener('DOMContentLoaded', function () {
        chat_main();
    });
}

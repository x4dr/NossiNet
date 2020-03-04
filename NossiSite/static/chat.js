$(document).ready(function(){
    let socket = io.connect('http://' + document.domain + ':' + location.port + '/chat');
    let charsocket = io.connect('http://' +  document.domain + ':' +location.port + '/character');
    let bell = new Audio("/static/bell.wav");
    let ring = false;
    let ringoverwrite = false;
    socket.on('Message', function(msg) {
        let box = $('#chatbox');
        box.append('<br>' + $('<div/>').text(msg.data).html());
        box.scrollTop(box[0].scrollHeight);
        if (ring){
            bell.play().then(r => r)
        }
    });

    charsocket.on('connect', function () {
        charsocket.emit('ClientServerEvent', {data: 'accessing character from chat'})
    });

    function keepAlive() {
        socket.emit('KeepAlive', {data:'blip'})
    }

    setInterval(keepAlive, 5000);

    function dotupdate(msg){
        let input = msg.data.split("§");
        let values = input[0].split("&");
        let maxima = input[1].split("&");
        let health = input[2].split("&");
        let Bloodpool= 0;
        let Bloodmax= 1;
        let Willpower= 0;
        let Willmax = 1;
        for (let i = 0; i < values.length; i++){
            if (values[i].split("_")[0] === "Bloodpool"){
                Bloodpool = parseInt(values[i].split("_")[1]);
                Bloodmax = parseInt(maxima[i].split("_")[1])
            }else {
                Willpower = parseInt(values[i].split("_")[1]);
                Willmax = parseInt(maxima[i].split("_")[1])
            }
        }
        document.getElementById("bloodbar").style.width = (100*Bloodpool/Bloodmax).toString()+"%";
        document.getElementById("willbar").style.width = (100*Willpower/Willmax).toString()+"%";
        let Bash= parseInt(health[0]);
        let Lethal= parseInt(health[1]);
        let Aggravated= parseInt(health[2]);
        let Partial= parseInt(health[3]);
        Aggravated = Aggravated-0.2*Partial;
        health = 7-(Bash+Lethal+Aggravated);
        document.getElementById("healthbar").style.width = (100*health/7).toString()+"%";
        document.getElementById("healthbar").style.left = (100*(Bash+Lethal+Aggravated)/7).toString()+"%";
        document.getElementById("bashbar").style.width = (100*Bash/7).toString()+"%";
        document.getElementById("bashbar").style.left = (100*(Lethal+Aggravated)/7).toString()+"%";
        document.getElementById("lethalbar").style.width = (100*Lethal/7).toString()+"%";
        document.getElementById("lethalbar").style.left = (100*(Aggravated)/7).toString()+"%";
        document.getElementById("aggbar").style.width = (100*Aggravated/7).toString()+"%";
    }

    charsocket.on('DotUpdate', function (msg) {
        dotupdate(msg)
    });

    socket.on('DotUpdate', function (msg) {
        dotupdate(msg)
    } );

    $(window).blur(function(){
        ring=!ringoverwrite
    });
    $(window).focus(function(){
        ring=false
    });

    socket.on('Status', function(msg) {
        document.getElementById('statusmessage').innerHTML = msg.status
    });

    socket.on('SetCmd', function(msg) {
        $('#message_data').val(msg.data)
    });

    socket.on('Exec', function(msg){
        eval(msg.command)

    });

    socket.on('connect', function() {
        socket.emit('ClientServerEvent', {data: '/connection established'});
        $('#message_data').focus();
    });

    let prevCommand = [];
    let commandCount = 0;
    let keyCount = 0;

    $('form#message').submit(function() {
        let message_data=$('#message_data').val();
        if (message_data==="/ring off"){
            ringoverwrite = true;
            document.getElementById('message_data').value = '';
            return false
        }
        if (message_data==="/ring on"){
            ringoverwrite = false;
            document.getElementById('message_data').value = '';
            return false
        }
        if(document.getElementById('message_data').value !== ''){
            socket.emit('ClientServerEvent',
                {data: message_data});
            commandCount++;
            keyCount = 0;
            prevCommand[commandCount] = message_data;
            document.getElementById('message_data').value = ''}
        return false;
    });

    $(document).keydown(function(event){
        let msgdata = $('#message_data');
        let index;
        if(event.which === 32){
            if (!msgdata.is(':focus')){
                msgdata.focus();
                return false
            }

        }

        if(event.which === 38){
            keyCount++;
            msgdata.focus();
            if(typeof prevCommand[keyCount] !== "undefined") {
                index = prevCommand.length-keyCount;
                msgdata.val(prevCommand[index]);
            } else {
                keyCount = 1;
                index = prevCommand.length-keyCount;
                msgdata.val(prevCommand[index]);
            }
            return false;
        }else if(event.which === 40) {
            keyCount--;
            msgdata.focus();
            if(typeof prevCommand[keyCount] !== "undefined") {
                index = prevCommand.length-keyCount;
                msgdata.val(prevCommand[index]);
                //  moveCursorToEnd(msgdata)
            } else {
                if (prevCommand[commandCount] !== msgdata.val() && msgdata.val() !== '' ) {
                    commandCount++;
                    keyCount = 0;
                    prevCommand[commandCount] = msgdata.val();
                }
                msgdata.val('')
            }
            return false;
        }
    });
});

#!/bin/bash
CONFDIR=/usr/local/bin/home-iot
KEY=$(awk -F "=" '/google_api_key/ {print $2}' $CONFDIR/conf.ini)
URL="https://speech.googleapis.com/v1/speech:recognize?key=$KEY"
AUDIODIR=/home/ina/VoiceCommands/
AUDFORMAT=mp3
MILIGHTIP=$(awk -F "=" '/milightip1/ {print $2}' $CONFDIR/conf.ini)
MILIGHTIP2=$(awk -F "=" '/milightip2/ {print $2}' $CONFDIR/conf.ini)
MILIGHTTOKEN=$(awk -F "=" '/milight_tok1/ {print $2}' $CONFDIR/conf.ini)
MILIGHTTOKEN2=$(awk -F "=" '/milight_tok2/ {print $2}' $CONFDIR/conf.ini)
MIVACIP=$(awk -F "=" '/mivac_ip/ {print $2}' $CONFDIR/conf.ini)
MIVACTOKEN=$(awk -F "=" '/mivac_token/ {print $2}' $CONFDIR/conf.ini)

echo Got Google key from config $URL
echo Got Token from config $MILIGHTTOKEN

function randomID() {
  maxval=$1
  randId=$(( ($RANDOM % $maxval)+1 ))
}

function playReply() {
  speechText=$1
  randomID $2
  mpg123 ${AUDIODIR}/${speechText}${randId}.${AUDFORMAT}  2> /dev/null
}

function strindex() {
  x="${1%%$2*}"
  [[ $x = $1 ]] && echo -1 || echo ${#x}
}




echo "Signal that wake word is detected and we're ready for a command"
playReply "Yes" 3
echo "Recording 10 sec mono audio"
arecord -D plughw:2,0 -f cd -t wav -d 3 -q -r 44100 -c 1 | flac - -s -f --best -o file.flac;
echo "Encoding in base64 as per Google standard"
base64 file.flac -w 0 > dest_audio_file.flac.base64
echo ""
> transcoded-text.txt
cat << EOF > sync-request.json
{
  "config": {
      "encoding":"FLAC",
      "sampleRateHertz": 44100,
      "languageCode": "bg-BG",
      "enableWordTimeOffsets": false
  },
  "audio": {
     "content": "`cat dest_audio_file.flac.base64`"
  }
}
EOF
echo "Request to Google API using curl"
curl -X POST -H "Content-Type: application/json; charset=utf-8" -o transcoded-text.txt --data @sync-request.json "https://speech.googleapis.com/v1/speech:recognize?key=$KEY"
 
echo -n "Google Answer: "
OUTPUT=$(cat transcoded-text.txt | grep "transcript"  | sed -e 's/[{},"]/''/g' | awk -F":" '{print $2}'  )
 
echo $OUTPUT
echo ""
 
#rm file.flac  > /dev/null 2>&1

OUTPUT=$(echo $OUTPUT | sed 's/[[:upper:]]*/\L&/' )

CMDRECOGNIZED=0
 
if (($(strindex "$OUTPUT" "вдигни щори") != -1));  then
  echo "Command recognized ! :  For opening shutters"
  playReply "CommandAccepted" 2
  /usr/bin/mosquitto_pub -h localhost -t 'shutters/command' -m "SEMIOPEN"
  CMDRECOGNIZED=1
fi

if (($(strindex "$OUTPUT" "пусни щори") != -1));  then
  echo "Command recognized ! : For closing shutters"
  playReply "CommandAccepted" 2
  /usr/bin/mosquitto_pub -h localhost -t 'shutters/command' -m "CLOSE"
  CMDRECOGNIZED=1
fi


if (($(strindex "$OUTPUT" "светни ламп") != -1)) || (($(strindex "$OUTPUT" "пусни ламп") != -1));  then
   echo "Command recognized ! : For turning on lights"
   playReply "Lights" 1
   miceil --ip $MILIGHTIP  --token $MILIGHTTOKEN on
   miceil --ip $MILIGHTIP2  --token $MILIGHTTOKEN2 on
   CMDRECOGNIZED=1
fi


if (($(strindex "$OUTPUT" "гаси ламп") != -1));  then
  echo "Command recognized ! : For shutting off lights"
  playReply "Lights" 1
  miceil --ip $MILIGHTIP  --token $MILIGHTTOKEN off
  miceil --ip $MILIGHTIP2  --token $MILIGHTTOKEN2 off
  CMDRECOGNIZED=1
fi


if (($(strindex "$OUTPUT" "мека светлина") != -1))   || (($(strindex "$OUTPUT" "романтика") != -1))  || (($(strindex "$OUTPUT" "намали ламп") != -1)) ;  then
  echo "Command recognized ! : For soft light"
  playReply "Lights" 1
  miceil --ip $MILIGHTIP  --token $MILIGHTTOKEN on
  miceil --ip $MILIGHTIP  --token $MILIGHTTOKEN set-brightness 20
  miceil --ip $MILIGHTIP  --token $MILIGHTTOKEN set-color-temperature 20
  miceil --ip $MILIGHTIP2  --token $MILIGHTTOKEN2 on
  miceil --ip $MILIGHTIP2  --token $MILIGHTTOKEN2 set-brightness 20
  miceil --ip $MILIGHTIP2  --token $MILIGHTTOKEN2 set-color-temperature 20
  CMDRECOGNIZED=1
fi

if (($(strindex "$OUTPUT" "усили ламп") != -1));  then
  echo "Command recognized ! : Turn up the light power"
  playReply "Lights" 1
  miceil --ip $MILIGHTIP --token $MILIGHTTOKEN set-brightness 100
  miceil --ip $MILIGHTIP --token $MILIGHTTOKEN set-color-temperature 30
  miceil --ip $MILIGHTIP2 --token $MILIGHTTOKEN2 set-brightness 100
  miceil --ip $MILIGHTIP2 --token $MILIGHTTOKEN2 set-color-temperature 30
  CMDRECOGNIZED=1
fi

if (($(strindex "$OUTPUT" "пусни прахосмукачка") != -1));  then
  echo "Command recognized ! : For vaccuming"
  playReply "CommandAccepted" 2
  mirobo --ip $MIVACIP  --token $MIVACTOKEN start
  CMDRECOGNIZED=1
fi

if (($(strindex "$OUTPUT" "при прахосмукачка") != -1));  then
  echo "Command recognized ! : For vaccum cleaner to return to dock"
  playReply "CommandAccepted" 2
  mirobo --ip $MIVACIP  --token $MIVACTOKEN home
  CMDRECOGNIZED=1
fi

if [ $CMDRECOGNIZED -eq 0 ]; then
  echo "No command recognized"
  playReply "UnknownCommand" 4
fi

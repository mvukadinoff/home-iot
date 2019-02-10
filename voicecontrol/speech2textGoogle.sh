#!/bin/bash
 
KEY=AIzaSyA9Q8G_tx85UUk5Qpi8buOLtbduhNZJUuc
URL="https://speech.googleapis.com/v1/speech:recognize?key=$KEY"
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
 
strindex() {
  x="${1%%$2*}"
  [[ $x = $1 ]] && echo -1 || echo ${#x}
}
 
OUTPUT=$(echo $OUTPUT | sed 's/[[:upper:]]*/\L&/' )
 
if (($(strindex "$OUTPUT" "вдигни щори") != -1));  then
  echo "Command recognized ! :  For opening shutters"
  /usr/bin/mosquitto_pub -h localhost -t 'shutters/command' -m "SEMIOPEN"
fi

if (($(strindex "$OUTPUT" "пусни щори") != -1));  then
  echo "Command recognized ! : For closing shutters"
  /usr/bin/mosquitto_pub -h localhost -t 'shutters/command' -m "CLOSE"
fi

#MILIGHTIP=192.168.1.23
MILIGHTIP=192.168.1.15

MILIGHTTOKEN=e876fafc013d49e67b07737f13382eba

if (($(strindex "$OUTPUT" "светни ламп") != -1)) || (($(strindex "$OUTPUT" "пусни ламп") != -1));  then
   echo "Command recognized ! : For turning on lights"
   miceil --ip $MILIGHTIP  --token $MILIGHTTOKEN on
fi


if (($(strindex "$OUTPUT" "гаси ламп") != -1));  then
  echo "Command recognized ! : For shutting off lights"
  miceil --ip $MILIGHTIP  --token $MILIGHTTOKEN off
fi


if (($(strindex "$OUTPUT" "мека светлина") != -1))   || (($(strindex "$OUTPUT" "романтика") != -1))  ;  then
  echo "Command recognized ! : For soft light"
  miceil --ip $MILIGHTIP  --token $MILIGHTTOKEN on
  miceil --ip $MILIGHTIP  --token $MILIGHTTOKEN set_brightness 20
  miceil --ip $MILIGHTIP  --token $MILIGHTTOKEN set_color_temperature 20
fi

if (($(strindex "$OUTPUT" "усили ламп") != -1));  then
  echo "Command recognized ! : Turn up the light power"
  miceil --ip $MILIGHTIP --token $MILIGHTTOKEN set_brightness 100
  miceil --ip $MILIGHTIP --token $MILIGHTTOKEN set_color_temperature 30
fi

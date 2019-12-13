mediasoupbin
============

GStreamer plugin for mediasoup-demo (https://github.com/vpalmisano/mediasoup-demo/). 

Install deps
------------

```sh
sudo apt install python3 python3-requests python3-gst-1.0 \
    gstreamer1.0-plugins-bad gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly \
    gstreamer1.0-tools gstreamer1.0-x gstreamer1.0-python3-plugin-loader \
    gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gir1.2-gst-plugins-bad-1.0
```

Install using git:

```sh
git clone https://github.com/vpalmisano/mediasoupbin.git
cd mediasoupbin
export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$PWD/gst/plugins
```

Install using pip:

```sh
pip3 install git+https://github.com/vpalmisano/mediasoupbin.git
export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$(python3 -m site --user-site)/gst/plugins
```

Producer mode
-------------

```sh
export PYTHON_DEBUG=5
export GST_DEBUG=2,python:5

gst-launch-1.0 \
    mediasoupbin_py name=ms server-url="https://localhost:4443/rooms/test" \
    videotestsrc is-live=true ! "video/x-raw,width=1280,height=720,framerate=25/1" ! ms. \
    audiotestsrc is-live=true wave=ticks ! "audio/x-raw" ! ms.
```

Consumer mode
-------------

```sh
# get the producers list from the server
curl -k "https://localhost:4443/rooms/test/broadcasters" | jq

gst-launch-1.0 mediasoupbin_py name=ms server-url="https://localhost:4443/rooms/test" local-ip=127.0.0.1 \
    ms. ! "video/x-raw,producer-id=<video producer id>" ! autovideosink sync=false \
    ms. ! "audio/x-raw,producer-id=<audio producer id>" ! autoaudiosink sync=false
```

Docker usage
------------

```sh
docker build -t mediasoupbin .

docker run --rm -it --net=host mediasoupbin \
    videotestsrc is-live=true ! "video/x-raw,width=1280,height=720,framerate=25/1" ! mediasoupbin_py
```

mediasoupbin
============

Install deps
------------

```sh
sudo apt install python3 python3-requests python3-gst-1.0 \
    gstreamer1.0-plugins-bad gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly \
    gstreamer1.0-tools gstreamer1.0-x gstreamer1.0-python3-plugin-loader \
    gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gir1.2-gst-plugins-bad-1.0
```

Docker
------

```sh
docker build -t mediasoupbin .

docker run --rm -it --net=host mediasoupbin \
    videotestsrc is-live=true ! "video/x-raw,width=1280,height=720,framerate=25/1" ! mediasoupbin_py
```

Producer mode
-------------

```sh
export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$PWD/gst/plugins
export PYTHON_DEBUG=5
export GST_DEBUG=2,python:5

gst-launch-1.0 \
    mediasoupbin_py name=ms \
    videotestsrc is-live=true ! "video/x-raw,width=1280,height=720,framerate=25/1" ! ms. \
    audiotestsrc is-live=true wave=ticks ! "audio/x-raw" ! ms.
```

Consumer mode
-------------

```sh
gst-launch-1.0 mediasoupbin_py name=ms \
    ms. ! "video/x-raw,producer-id=test_video" ! xvimagesink sync=false \
    ms. ! "audio/x-raw,producer-id=test_audio" ! pulsesink sync=false
```

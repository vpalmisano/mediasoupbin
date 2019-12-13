
```sh
export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$PWD/gst/plugins
export PYTHON_DEBUG=5
export GST_DEBUG=2,python:5

# send to a/v producers
gst-launch-1.0 \
    mediasoupbin_py name=ms \
    videotestsrc is-live=true ! "video/x-raw,width=1280,height=720,framerate=25/1" ! ms. \
    audiotestsrc is-live=true wave=ticks ! "audio/x-raw" ! ms.

# receive from a/v producers
gst-launch-1.0 mediasoupbin_py name=ms \
    ms. ! "video/x-raw,producer-id=test_video" ! xvimagesink sync=false \
    ms. ! "audio/x-raw,producer-id=test_audio" ! pulsesink sync=false
```

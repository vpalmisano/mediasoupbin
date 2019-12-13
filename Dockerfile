FROM debian:buster-slim
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -yq --no-install-recommends \
        sudo localepurge git curl gnupg ffmpeg vainfo i965-va-driver xz-utils \
        fonts-roboto python3 python3-requests python3-pip python3-gst-1.0 gstreamer1.0-vaapi gstreamer1.0-pulseaudio \
        gstreamer1.0-nice gstreamer1.0-libav gstreamer1.0-plugins-bad gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly gstreamer1.0-tools gstreamer1.0-x gstreamer1.0-python3-plugin-loader \
        gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gir1.2-gst-plugins-bad-1.0 gir1.2-soup-2.4 gir1.2-gtk-3.0 \   
        xvfb mesa-utils xserver-xorg-video-all xdotool libgl1-mesa-glx libgl1-mesa-dri xauth \
        libasound2 libasound2-plugins alsa-utils alsa-oss pulseaudio pulseaudio-utils xserver-xephyr \
        python3-setuptools python3-opengl python3-psutil python3-gi-cairo
RUN apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /
COPY gst/plugins/python /usr/lib/x86_64-linux-gnu/gstreamer-1.0/python/
ENTRYPOINT [ "gst-launch-1.0" ]
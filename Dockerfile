FROM debian:bookworm-slim

ARG JDK_URL
ARG JDK_SHA256

RUN test -n "$JDK_URL" && test -n "$JDK_SHA256" \
    && apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates curl libstdc++6 zlib1g \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fL --retry 3 --retry-delay 2 "$JDK_URL" -o /tmp/jdk.tar.gz \
    && printf '%s  %s\n' "$JDK_SHA256" /tmp/jdk.tar.gz | sha256sum -c - \
    && mkdir -p /opt/jdk \
    && tar -xzf /tmp/jdk.tar.gz -C /opt/jdk --strip-components=1 \
    && rm /tmp/jdk.tar.gz

COPY Base64TailProbe.java /opt/probe/Base64TailProbe.java
RUN /opt/jdk/bin/javac /opt/probe/Base64TailProbe.java

WORKDIR /opt/probe
ENTRYPOINT ["/opt/jdk/bin/java"]
CMD ["-XX:UseAVX=3", "-cp", "/opt/probe", "Base64TailProbe"]

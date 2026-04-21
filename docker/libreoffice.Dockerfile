FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    fonts-dejavu \
    fonts-liberation \
    curl \
    python3 \
 && rm -rf /var/lib/apt/lists/*

# Listen on TCP socket for headless conversion requests.
EXPOSE 2002

# Run LibreOffice as a headless UNO server. The backend calls this via
# `unoconv` / socket to convert docx → pdf.
CMD ["soffice", \
     "--headless", \
     "--nologo", \
     "--nofirststartwizard", \
     "--accept=socket,host=0.0.0.0,port=2002;urp;", \
     "--norestore"]

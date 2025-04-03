FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
        ENV PORT=8501
        EXPOSE $PORT
        WORKDIR /dhlab_alto_viewer.py

        COPY requirements.txt ./requirements.txt
        RUN uv pip install --system --compile-bytecode --only-binary=:all: --no-binary=python-louvain -r requirements.txt

        COPY app.py alto_utils.py download_utils.py image_utils.py metadata_utils.py  ./

        # Warm up caches
        RUN python -c 'import streamlit, dhlab, requests, pandas, matplotlib'
        RUN timeout 5s streamlit hello; exit 0

        CMD streamlit run app.py                \
            --server.port ${PORT}               \
            --browser.gatherUsageStats=False    \
            --server.baseUrlPath /alto-viewer


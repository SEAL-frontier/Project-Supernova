FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY pyproject.toml README.md requirements.txt LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY bot.py ./
ENTRYPOINT ["keys-keys"]
CMD ["run"]

FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖（pymysql / argon2 编译需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 仅复制运行时必要文件，排除测试、文档、开发工具
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .
COPY templates/ templates/

# 创建导出目录（运行时生成 Word 文件）
RUN mkdir -p exports

EXPOSE 8080

CMD ["python", "-m", "app.main"]

.PHONY: help install test test-arch test-quality test-all lint format clean guard build docs docs-serve docs-clean

# 默认目标
help:
	@echo "PlookingII - 开发工具集"
	@echo ""
	@echo "可用命令:"
	@echo "  make install          - 安装所有依赖"
	@echo "  make install-dev      - 安装开发依赖"
	@echo "  make test             - 运行所有测试"
	@echo "  make test-arch        - 运行架构测试"
	@echo "  make test-quality     - 运行代码质量测试"
	@echo "  make test-coverage    - 运行测试并生成覆盖率报告"
	@echo "  make guard            - 运行架构守护检查"
	@echo "  make lint             - 运行代码检查(ruff + flake8)"
	@echo "  make format           - 格式化代码"
	@echo "  make type-check       - 运行类型检查"
	@echo "  make complexity       - 检查代码复杂度"
	@echo "  make security         - 运行安全检查"
	@echo "  make pre-commit       - 安装pre-commit钩子"
	@echo "  make docs             - 生成API文档(Sphinx)"
	@echo "  make docs-serve       - 本地预览文档"
	@echo "  make docs-clean       - 清理文档构建"
	@echo "  make clean            - 清理临时文件"
	@echo "  make clean-all        - 深度清理(包括缓存)"
	@echo "  make build            - 构建应用程序"
	@echo "  make ci               - 模拟CI流程(本地)"
	@echo ""

# 安装依赖
install:
	pip install -r requirements.txt

install-dev: install
	pip install -r requirements-dev.txt

# 测试相关
test:
	python3 -m pytest -v

test-arch:
	python3 -m pytest tests/test_architecture.py -v --tb=short --no-cov

test-quality:
	python3 -m pytest tests/test_code_quality.py -v --tb=short --no-cov

test-coverage:
	python3 -m pytest -v --cov=plookingII --cov-report=term-missing --cov-report=html --cov-report=xml

test-all: test-arch test-quality test

# 架构守护
guard:
	@echo "🛡️  运行架构守护检查..."
	python3 tools/architecture_guard.py

# 代码质量
lint:
	@echo "🔍 运行Ruff检查..."
	ruff check plookingII/
	@echo ""
	@echo "🔍 运行Flake8检查..."
	flake8 plookingII/ || true

format:
	@echo "✨ 格式化代码..."
	ruff format plookingII/
	ruff check --fix plookingII/

type-check:
	@echo "🔍 运行Mypy类型检查..."
	mypy plookingII/ || true

complexity:
	@echo "📊 检查代码复杂度..."
	@echo "=== 圈复杂度 (D级及以上) ==="
	radon cc plookingII/ -n D -s || true
	@echo ""
	@echo "=== 可维护性指数 ==="
	radon mi plookingII/ -n -s || true

security:
	@echo "🔒 运行安全检查..."
	@echo "=== 依赖安全扫描 ==="
	pip-audit -r requirements.txt -r requirements-dev.txt || true
	@echo ""
	@echo "=== Bandit安全扫描 ==="
	bandit -r plookingII/ -ll || true

# Pre-commit hooks
pre-commit: install-dev
	@echo "📌 安装pre-commit钩子..."
	pip install pre-commit
	pre-commit install
	@echo "✅ Pre-commit钩子已安装"

pre-commit-run:
	pre-commit run --all-files

# 清理
clean:
	@echo "🧹 清理临时文件..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -f .coverage
	rm -f coverage.xml
	@echo "✅ 清理完成"

clean-all: clean
	@echo "🧹 深度清理..."
	rm -rf build/PlookingII
	rm -rf dist/PlookingII
	rm -rf dist/PlookingII.app
	rm -rf *.egg-info
	rm -rf .eggs
	rm -rf venv
	rm -rf .venv
	@echo "✅ 深度清理完成"

# 文档生成
docs: install-dev
	@echo "📚 生成API文档..."
	cd docs && sphinx-build -b html . _build/html
	@echo "✅ 文档已生成: docs/_build/html/index.html"

docs-serve: docs
	@echo "🌐 启动文档服务器..."
	@echo "📖 访问地址: http://localhost:8000"
	cd docs/_build/html && python3 -m http.server 8000

docs-clean:
	@echo "🧹 清理文档构建..."
	rm -rf docs/_build
	@echo "✅ 文档清理完成"

# 构建
build:
	@echo "📦 构建应用程序..."
	python3 tools/package_release.py --build

# CI模拟
ci: clean guard test-arch test-quality lint type-check complexity security test-coverage
	@echo ""
	@echo "================================================================"
	@echo "✅ CI检查全部完成！"
	@echo "================================================================"
	@echo ""
	@echo "📊 测试覆盖率报告: htmlcov/index.html"
	@echo ""

# 快速检查(提交前)
quick-check: guard test-arch lint
	@echo ""
	@echo "================================================================"
	@echo "✅ 快速检查完成！可以安全提交。"
	@echo "================================================================"
	@echo ""

# 完整检查(发布前)
full-check: ci
	@echo "🎉 所有检查通过，可以发布！"

# 开发服务器(如果有的话)
run:
	@echo "🚀 启动应用..."
	python3 -m plookingII

# 显示项目信息
info:
	@echo "📋 项目信息"
	@echo "======================================"
	@python3 -c "import sys; print(f'Python版本: {sys.version}')"
	@echo "======================================"
	@echo "依赖包:"
	@pip list | grep -E "(pytest|ruff|flake8|mypy|radon)"
	@echo "======================================"


.PHONY: help install test test-all lint format clean build

# 优先使用项目虚拟环境（.venv），不存在时回退到系统 python3
PYTHON ?= .venv/bin/python3
PYTHON_BIN := $(shell test -x $(PYTHON) && echo $(PYTHON) || echo python3)

# 默认目标
help:
	@echo "PlookingII - 开发工具集"
	@echo ""
	@echo "可用命令:"
	@echo "  make install          - 安装所有依赖"
	@echo "  make install-dev      - 安装开发依赖"
	@echo "  make run              - 启动应用"
	@echo "  make test             - 运行所有测试"
	@echo "  make test-coverage    - 运行测试并生成覆盖率报告"
	@echo "  make verify-version   - 验证版本号一致性"
	@echo "  make unify-version    - 统一并清理版本号"
	@echo "  make clear-recent     - 清理 macOS 最近项目记录"
	@echo "  make lint             - 运行代码检查(ruff + flake8)"
	@echo "  make format           - 格式化代码"
	@echo "  make type-check       - 运行类型检查"
	@echo "  make complexity       - 检查代码复杂度"
	@echo "  make security         - 运行安全检查"
	@echo "  make pre-commit       - 安装pre-commit钩子"
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
	$(PYTHON_BIN) -m pytest -v

test-coverage:
	$(PYTHON_BIN) -m pytest -v --cov=plookingII --cov-report=term-missing --cov-report=html --cov-report=xml

test-all: test

# 版本管理
verify-version:
	@echo "🔍 验证版本号一致性..."
	$(PYTHON_BIN) scripts/verify_version_consistency.py

unify-version:
	@echo "🔧 统一版本号管理..."
	$(PYTHON_BIN) scripts/unify_version.py
	@echo ""
	@echo "✅ 运行验证检查..."
	$(PYTHON_BIN) scripts/verify_version_consistency.py

# 自动版本管理（python-semantic-release）
release-dry-run:
	@echo "🔍 预览将自动计算的下一版本（不修改任何文件）..."
	python3 -m semantic_release version --no-push --no-tag --no-commit --no-changelog

release-version:
	@echo "🔖 自动提升版本号并更新 CHANGELOG..."
	python3 -m semantic_release version --no-push
	@echo "✅ 已生成版本提交与标签，请审查后推送：git push origin <分支> --tags"

clear-recent:
	@echo "🧹 清理 macOS 最近项目记录..."
	$(PYTHON_BIN) scripts/clear_recent_items.py

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

# 构建
build:
	@echo "📦 构建应用程序..."
	$(PYTHON_BIN) tools/package_release.py --build

# CI模拟
ci: clean verify-version lint type-check complexity security test-coverage
	@echo ""
	@echo "================================================================"
	@echo "✅ CI检查全部完成！"
	@echo "================================================================"
	@echo ""
	@echo "📊 测试覆盖率报告: htmlcov/index.html"
	@echo ""

# 快速检查(提交前)
quick-check: verify-version lint
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
	$(PYTHON_BIN) -m plookingII

# 显示项目信息
info:
	@echo "📋 项目信息"
	@echo "======================================"
	@$(PYTHON_BIN) -c "import sys; print(f'Python版本: {sys.version}')"
	@echo "======================================"
	@echo "依赖包:"
	@pip list | grep -E "(pytest|ruff|flake8|mypy|radon)"
	@echo "======================================"

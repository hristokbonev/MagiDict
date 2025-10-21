# Contributing to MagiDict

Thank you for your interest in contributing to MagiDict!

## How to Contribute

- **Report bugs** or **suggest features** via [GitHub Issues](https://github.com/yourusername/magidict/issues)
- **Fix bugs** or **add features** with pull requests
- **Improve documentation** and add examples
- **Write tests** to increase coverage

## Development Setup

```bash
# Fork and clone the repository
git clone https://github.com/YOUR-USERNAME/magidict.git
cd magidict

# Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"

# Build C extensions (optional)
python setup.py build_ext --inplace
```

## Code Guidelines

- Formatters and linters:
  ```bash
  black magidict/
  flake8 magidict/
  mypy magidict/
  ```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=magidict

# Aim for 90%+ coverage on new features
```

Please aim to include appropriate tests covering both success and edge cases.

## Pull Request Process

1. **Create a branch**: `git checkout -b feature/your-feature-name`
2. **Make your changes** with commit messages
3. **Run tests**
4. **Update documentation** if needed
5. **Submit PR** with:
   - Description of changes
   - Reference to related issues
   - Note any breaking changes

## Notes

- **Preserve backward compatibility** when possible
- **Document breaking changes**
- **Handle edge cases**: None values, circular references, deep nesting, pickleability, etc.

## License

By contributing, you agree that your contributions will be licensed under the MIT License. Please ensure that your code does not violate any third-party licenses.

---

Thank you for making MagiDict better!

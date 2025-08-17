#!/usr/bin/env bash
# Install git-helpers Python modules
python -c "import site; import os; p=site.getsitepackages()[0]; os.symlink('$HOME/.rc/git-helpers.pth', os.path.join(p, 'git-helpers.pth'))" 2>/dev/null || echo "git-helpers.pth already installed"
echo "git-helpers Python modules installed. You can now use: from util.branch_resolution import ..."
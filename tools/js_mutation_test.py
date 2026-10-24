"""前端 JS 的變異測試。

cosmic-ray 只能變異 Python，所以這裡對 static/javascripts/ 定義一組變異，
每個變異都在暫存的專案副本裡跑一次 tests/e2e，確認測試會失敗（mutant 被殺掉）。
專案本身的檔案不會被修改。

用法：python tools/js_mutation_test.py
有非等價的 mutant 存活時 exit code 為 1。
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST_COMMAND = [sys.executable, '-m', 'pytest', '-x', '-q', '-p', 'no:cacheprovider', 'tests/e2e']
TIMEOUT = 300

# (檔案, 原本的程式碼, 改成的程式碼, 等價的原因或 None)
MUTANTS = [
    ('register.js', "headers: { 'X-CSRFToken': csrfToken },", '', None),
    ('register.js', 'if (ok) {', 'if (!ok) {', None),
    ('register.js', 'await checkUsername();', '', None),
    ('register.js', '        lastCheck = null;\n', '', None),
    ('register.js', 'if (username.value.trim() !== value) return;', '', None),
    ('register.js', 'return lastCheck.promise;', 'return;', None),
    ('register.js', 'if (!lastCheck || lastCheck.value !== value) {', 'if (!lastCheck) {',
     '名稱一改就會觸發 input 事件清掉 lastCheck，比對名稱只是防禦性寫法'),
    ('picture.js', "headers: { 'X-CSRFToken': csrfToken }, ", '', None),
    ('picture.js', 'selection.aspectRatio = 1;', '', None),
    ('picture.js', '{ width: 256, height: 256 }', '{ width: 128, height: 128 }', None),
    ('picture.js', 'location.reload();', '', None),
    ('index.js', 'document.createTextNode(data.msg)', 'document.createRange().createContextualFragment(data.msg)',
     None),
    ('index.js', "if (e.key === 'Enter' && !e.shiftKey)", "if (e.key === 'Enter')", None),
    ('index.js', 'if (!msg) return;', '', None),
    ('index.js', "messageInput.value = '';", '', None),
    ('index.js', "messageSubmit.addEventListener('click', insertMessage);", '', None),
    ('index.js', 'pad(d.getHours())', 'pad(d.getUTCHours())', None),
    ('index.js', 'pad(d.getMonth() + 1)', 'pad(d.getMonth())', None),
    ('index.js', 'el.textContent = formatTime(el.dateTime);', '', None),
    ('login.js', 'e.preventDefault();', '', None),
]


def run_tests(workdir):
    try:
        result = subprocess.run(TEST_COMMAND, cwd=workdir, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return False
    return result.returncode == 0


def main():
    workdir = Path(tempfile.mkdtemp(prefix='js-mutation-'))
    try:
        shutil.copytree(ROOT, workdir, dirs_exist_ok=True, ignore=shutil.ignore_patterns(
            '.git', '__pycache__', '.pytest_cache', 'instance', 'session.sqlite'))
        if not run_tests(workdir):
            print('baseline: tests/e2e 在沒有變異的情況下就失敗了，先修好測試再跑變異測試')
            return 1

        unexpected = 0
        for name, old, new, equivalent in MUTANTS:
            path = workdir / 'static' / 'javascripts' / name
            original = path.read_text(encoding='utf-8')
            if original.count(old) != 1:
                print('ERROR    {}: 找不到唯一的 {!r}，變異清單需要更新'.format(name, old.strip()))
                unexpected += 1
                continue
            path.write_text(original.replace(old, new), encoding='utf-8')
            try:
                survived = run_tests(workdir)
            finally:
                path.write_text(original, encoding='utf-8')

            if not survived:
                outcome = 'KILLED  '
            elif equivalent:
                outcome = 'SURVIVED (等價：{})'.format(equivalent)
            else:
                outcome = 'SURVIVED'
                unexpected += 1
            print('{} {}: {!r} -> {!r}'.format(outcome, name, old.strip(), new.strip()), flush=True)

        print('\n{} 個 mutants，非預期存活 {} 個'.format(len(MUTANTS), unexpected))
        return 1 if unexpected else 0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())

---
title: Python os 模块使用指南
description: os 模块的路径操作、文件与目录管理、进程控制、环境变量与文件描述符用法
tags:
  - python
  - stdlib
  - os
date: 2026-11-06
aliases:
  - os-module-guide
---

# Python os 模块使用指南

## 目录

1. [模块简介](#模块简介)
2. [路径操作](#路径操作-os.path)
3. [文件和目录操作](#文件和目录操作)
4. [进程管理](#进程管理)
5. [环境变量和系统信息](#环境变量和系统信息)
6. [文件描述符和I/O](#文件描述符和io)
7. [错误和异常处理](#错误和异常处理)
8. [实用示例](#实用示例)
9. [最佳实践](#最佳实践)

---

## 模块简介

`os`模块是Python标准库的核心模块之一，提供了与操作系统交互的接口。它允许你在Python程序中执行文件和目录操作、进程管理、环境变量访问等系统级操作。

### 导入方式

```python
import os
# 或导入特定功能
from os import listdir, getcwd
```

---

## 路径操作 (`os.path`)

这是`os`模块中最常用的子模块，用于跨平台路径处理。

### 基本路径操作

```python
import os

# 当前工作目录
current_dir = os.getcwd()  # 获取当前工作目录
os.chdir('/new/path')      # 改变工作目录

# 路径拼接
path = os.path.join('dir1', 'dir2', 'file.txt')  # 自动处理分隔符
# Windows: dir1\dir2\file.txt
# Linux/macOS: dir1/dir2/file.txt

# 路径拆分
directory, filename = os.path.split('/home/user/file.txt')
# directory = '/home/user', filename = 'file.txt'

basename = os.path.basename('/home/user/file.txt')  # 'file.txt'
dirname = os.path.dirname('/home/user/file.txt')    # '/home/user'
filename, ext = os.path.splitext('data.csv')        # ('data', '.csv')
```

### 路径检查和规范化

```python
# 获取绝对路径
abs_path = os.path.abspath('file.txt')

# 规范化路径（清理..和.）
norm_path = os.path.normpath('/home/user/../user/file.txt')
# 结果: /home/user/file.txt

# 相对路径
rel_path = os.path.relpath('/home/user/file.txt', '/home')
# 结果: user/file.txt

# 检查路径是否存在
exists = os.path.exists('/some/path')
is_file = os.path.isfile('/path/to/file')
is_dir = os.path.isdir('/path/to/dir')
is_abs = os.path.isabs('/absolute/path')
is_link = os.path.islink('/path/to/link')
```

### 路径信息获取

```python
# 文件大小（字节）
size = os.path.getsize('file.txt')

# 文件时间戳
mtime = os.path.getmtime('file.txt')  # 最后修改时间
atime = os.path.getatime('file.txt')  # 最后访问时间
ctime = os.path.getctime('file.txt')  # 创建时间/元数据修改时间

# 转换为可读格式
from datetime import datetime
dt = datetime.fromtimestamp(mtime)
print(f"最后修改: {dt.strftime('%Y-%m-%d %H:%M:%S')}")

# 获取真实路径（解析符号链接）
real_path = os.path.realpath('/path/to/link')
```

---

## 文件和目录操作

### 目录操作

```python
# 列出目录内容
files = os.listdir('.')  # 当前目录下所有文件和目录
for item in os.listdir('.'):
    if os.path.isfile(item):
        print(f"文件: {item}")
    elif os.path.isdir(item):
        print(f"目录: {item}")

# 递归遍历目录树
for root, dirs, files in os.walk('.'):
    print(f"当前目录: {root}")
    print(f"子目录: {dirs}")
    print(f"文件: {files}")
    print("-" * 40)

# 创建和删除目录
os.mkdir('new_dir')               # 创建单级目录
os.makedirs('dir1/dir2/dir3')     # 创建多级目录（已存在不会报错）
os.makedirs('dir1/dir2/dir3', exist_ok=True)  # 存在时不报错

os.rmdir('empty_dir')             # 删除空目录
# 删除非空目录（递归删除）
import shutil
shutil.rmtree('dir_with_content')
```

### 文件操作

```python
# 创建文件
with open('new_file.txt', 'w') as f:
    f.write('Hello, World!')

# 文件重命名/移动
os.rename('old_name.txt', 'new_name.txt')
os.replace('source.txt', 'dest.txt')  # 原子操作，覆盖已存在的文件

# 复制文件
import shutil
shutil.copy2('source.txt', 'dest.txt')  # 保留元数据
shutil.copy('source.txt', 'dest.txt')   # 不保留元数据

# 删除文件
os.remove('file_to_delete.txt')
os.unlink('file_to_delete.txt')  # 同remove

# 创建和读取链接
os.symlink('target.txt', 'link.txt')  # 创建符号链接
os.link('source.txt', 'hardlink.txt')  # 创建硬链接
```

### 文件权限和属性

```python
# 修改文件权限
os.chmod('file.txt', 0o755)  # 八进制表示
# 等价于
os.chmod('file.txt', 
         os.R_OK | os.W_OK | os.X_OK)  # 可读|可写|可执行

# 检查权限
can_read = os.access('file.txt', os.R_OK)
can_write = os.access('file.txt', os.W_OK)
can_exec = os.access('file.txt', os.X_OK)
exists = os.access('file.txt', os.F_OK)

# 修改所有者和组（Unix-like系统）
os.chown('file.txt', uid, gid)  # 需要root权限

# 修改时间戳
# 设置最后访问和修改时间
timestamp = 1609459200  # Unix时间戳
os.utime('file.txt', (timestamp, timestamp))

# 设置访问和修改时间为当前时间
os.utime('file.txt', None)
```

---

## 进程管理

### 执行系统命令

```python
# 执行命令并获取退出码
exit_code = os.system('ls -la')

# 执行命令并获取输出
result = os.popen('ls -la').read()
print(result)

# 现代替代方案（Python 3.5+）
import subprocess
result = subprocess.run(['ls', '-la'], capture_output=True, text=True)
print(result.stdout)
```

### 进程控制

```python
# 获取进程ID
pid = os.getpid()       # 当前进程ID
ppid = os.getppid()    # 父进程ID

# 进程相关操作
os.kill(pid, signal.SIGTERM)  # 发送信号
os.abort()                     # 中止当前进程
os._exit(0)                   # 立即退出，不执行清理

# 创建子进程
pid = os.fork()  # Unix-like系统专用
if pid == 0:
    # 子进程代码
    print("我是子进程")
    os._exit(0)
else:
    # 父进程代码
    print(f"子进程ID: {pid}")
    os.waitpid(pid, 0)  # 等待子进程结束
```

### 系统信息

```python
# 用户信息
username = os.getlogin()  # 当前登录用户名
uid = os.getuid()         # 当前用户ID（Unix）
gid = os.getgid()         # 当前组ID（Unix）

# 系统标识
import platform
system = platform.system()  # 'Linux', 'Windows', 'Darwin'
release = platform.release()  # 系统版本

# CPU核心数
cpu_count = os.cpu_count()

# 终端信息
if os.isatty(0):  # 检查标准输入是否是终端
    print("运行在终端中")
    
columns, lines = os.get_terminal_size()  # 终端大小
print(f"终端大小: {columns}x{lines}")
```

---

## 环境变量和系统信息

### 环境变量操作

```python
# 获取环境变量
home = os.environ.get('HOME')
path = os.environ.get('PATH')

# 安全获取（带默认值）
python_path = os.environ.get('PYTHONPATH', '/default/path')

# 设置环境变量
os.environ['MY_VAR'] = 'my_value'

# 更新环境变量（临时）
os.environ.update({
    'VAR1': 'value1',
    'VAR2': 'value2'
})

# 删除环境变量
if 'MY_VAR' in os.environ:
    del os.environ['MY_VAR']

# 获取所有环境变量
for key, value in os.environ.items():
    print(f"{key}={value}")
```

### 系统路径

```python
# 获取用户目录
user_home = os.path.expanduser('~')
desktop = os.path.expanduser('~/Desktop')

# 系统临时目录
temp_dir = os.environ.get('TMPDIR', 
                         os.environ.get('TEMP', 
                                       os.environ.get('TMP', '/tmp')))
# 或使用标准库
import tempfile
temp_dir = tempfile.gettempdir()

# 可执行文件搜索路径
path_dirs = os.environ.get('PATH', '').split(os.pathsep)
```

---

## 文件描述符和I/O

### 低级文件操作

```python
# 使用文件描述符
fd = os.open('file.txt', os.O_RDWR | os.O_CREAT)  # 打开文件
content = os.read(fd, 100)  # 读取100字节
os.write(fd, b'New content')  # 写入字节数据
os.lseek(fd, 0, os.SEEK_SET)  # 移动文件指针
os.close(fd)  # 关闭文件描述符

# 文件描述符复制
new_fd = os.dup(fd)  # 复制文件描述符
os.dup2(old_fd, new_fd)  # 复制到指定描述符
```

### 管道和文件锁

```python
# 创建管道
r, w = os.pipe()  # 返回读端和写端的文件描述符

# 文件锁（Unix-like系统）
import fcntl
with open('file.txt', 'r+') as f:
    # 非阻塞锁
    try:
        fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # 执行操作
        fcntl.lockf(f, fcntl.LOCK_UN)  # 解锁
    except BlockingIOError:
        print("文件被其他进程锁定")
```

### 内存映射文件

```
import mmap

with open('large_file.bin', 'r+b') as f:
    # 创建内存映射
    mm = mmap.mmap(f.fileno(), 0)
    
    # 随机访问
    data = mm[1000:2000]  # 读取1000字节
    mm[5000:5010] = b'New data'  # 写入数据
    
    mm.close()  # 关闭内存映射
```

---

## 错误和异常处理

### 常见异常

```python
import os
import errno

try:
    os.remove('non_existent_file.txt')
except FileNotFoundError:
    print("文件不存在")
except PermissionError:
    print("权限不足")
except OSError as e:
    if e.errno == errno.ENOENT:
        print("文件不存在")
    elif e.errno == errno.EACCES:
        print("权限不足")
    else:
        print(f"系统错误: {e}")

# 检查文件存在性
if not os.path.exists('file.txt'):
    print("文件不存在")

# 检查目录是否为空
def is_dir_empty(dirpath):
    try:
        return len(os.listdir(dirpath)) == 0
    except FileNotFoundError:
        return True
    except PermissionError:
        print(f"无权限访问目录: {dirpath}")
        return False
```

### 错误代码

```python
import errno

# 常见错误码
ERRORS = {
    errno.ENOENT: "文件或目录不存在",
    errno.EACCES: "权限不足",
    errno.ENOSPC: "磁盘空间不足",
    errno.EEXIST: "文件已存在",
    errno.EINVAL: "无效参数",
    errno.ENOTEMPTY: "目录非空"
}

def handle_os_error(e):
    """处理操作系统错误"""
    error_msg = ERRORS.get(e.errno, str(e))
    print(f"错误: {error_msg}")
```

---

## 实用示例

### 示例1：目录清理工具

```python
import os
import time
import shutil
from datetime import datetime, timedelta

def clean_old_files(directory, days_old=30, extensions=None):
    """
    清理指定天数前的文件
    """
    cutoff_time = time.time() - (days_old * 24 * 3600)
    deleted = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            # 检查扩展名
            if extensions and not file.endswith(tuple(extensions)):
                continue
                
            filepath = os.path.join(root, file)
            try:
                # 检查文件修改时间
                if os.path.getmtime(filepath) < cutoff_time:
                    os.remove(filepath)
                    deleted.append(filepath)
                    print(f"删除: {filepath}")
            except (PermissionError, OSError) as e:
                print(f"无法删除 {filepath}: {e}")
    
    return deleted

# 使用示例
clean_old_files('/tmp/logs', days_old=7, extensions=('.log', '.txt'))
```

### 示例2：文件同步工具

```python
import os
import hashlib
import shutil

def calculate_checksum(filepath):
    """计算文件校验和"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def sync_directories(source, destination):
    """同步两个目录"""
    operations = {'copied': 0, 'deleted': 0, 'skipped': 0}
    
    # 确保目标目录存在
    os.makedirs(destination, exist_ok=True)
    
    # 收集源文件信息
    source_files = {}
    for root, dirs, files in os.walk(source):
        rel_path = os.path.relpath(root, source)
        target_dir = os.path.join(destination, rel_path)
        os.makedirs(target_dir, exist_ok=True)
        
        for file in files:
            src_file = os.path.join(root, file)
            dst_file = os.path.join(target_dir, file)
            
            # 比较文件
            if not os.path.exists(dst_file):
                # 目标文件不存在，直接复制
                shutil.copy2(src_file, dst_file)
                operations['copied'] += 1
            else:
                # 比较文件大小和修改时间
                src_stat = os.stat(src_file)
                dst_stat = os.stat(dst_file)
                
                if (src_stat.st_size != dst_stat.st_size or
                    src_stat.st_mtime > dst_stat.st_mtime):
                    # 文件不同，复制更新
                    shutil.copy2(src_file, dst_file)
                    operations['copied'] += 1
                else:
                    operations['skipped'] += 1
    
    # 清理目标目录中不存在的文件
    for root, dirs, files in os.walk(destination):
        rel_path = os.path.relpath(root, destination)
        source_dir = os.path.join(source, rel_path)
        
        if not os.path.exists(source_dir):
            # 源目录不存在，删除整个目录
            shutil.rmtree(root)
            operations['deleted'] += 1
            continue
            
        for file in files:
            dst_file = os.path.join(root, file)
            src_file = os.path.join(source_dir, file)
            
            if not os.path.exists(src_file):
                os.remove(dst_file)
                operations['deleted'] += 1
    
    return operations

# 使用示例
sync_directories('/path/to/source', '/path/to/backup')
```

### 示例3：批量重命名工具

```python
import os
import re
from pathlib import Path

def batch_rename(directory, pattern, replacement, 
                 file_ext=None, recursive=False):
    """
    批量重命名文件
    """
    renamed = []
    
    if recursive:
        # 递归处理
        file_list = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_list.append(os.path.join(root, file))
    else:
        # 仅当前目录
        file_list = [os.path.join(directory, f) 
                    for f in os.listdir(directory) 
                    if os.path.isfile(os.path.join(directory, f))]
    
    for filepath in file_list:
        # 检查扩展名
        if file_ext and not filepath.endswith(file_ext):
            continue
        
        dirname, filename = os.path.split(filepath)
        new_name = re.sub(pattern, replacement, filename)
        
        if new_name != filename:
            new_path = os.path.join(dirname, new_name)
            
            # 避免文件名冲突
            counter = 1
            while os.path.exists(new_path):
                name, ext = os.path.splitext(new_name)
                new_path = os.path.join(dirname, 
                                      f"{name}_{counter}{ext}")
                counter += 1
            
            os.rename(filepath, new_path)
            renamed.append((filepath, new_path))
            print(f"重命名: {filename} -> {os.path.basename(new_path)}")
    
    return renamed

# 使用示例
batch_rename(
    directory='./photos',
    pattern=r'^IMG_(\d{4})\.jpg$',
    replacement=r'photo_\1.jpg',
    file_ext='.jpg',
    recursive=True
)
```

### 示例4：查找重复文件

```python
import os
import hashlib
from collections import defaultdict

def find_duplicate_files(directory):
    """查找重复文件（基于内容）"""
    hashes = defaultdict(list)
    
    for root, dirs, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            
            try:
                # 计算文件哈希
                with open(filepath, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                
                hashes[file_hash].append(filepath)
            except (IOError, OSError) as e:
                print(f"无法读取文件 {filepath}: {e}")
                continue
    
    # 返回重复的文件
    duplicates = {h: paths for h, paths in hashes.items() 
                  if len(paths) > 1}
    
    return duplicates

def delete_duplicates(duplicates, keep_first=True):
    """删除重复文件"""
    deleted = []
    
    for file_hash, filepaths in duplicates.items():
        # 保留第一个文件
        if keep_first:
            to_delete = filepaths[1:]
        else:
            to_delete = filepaths[:-1]
        
        for filepath in to_delete:
            try:
                os.remove(filepath)
                deleted.append(filepath)
                print(f"删除: {filepath}")
            except (PermissionError, OSError) as e:
                print(f"无法删除 {filepath}: {e}")
    
    return deleted

# 使用示例
duplicates = find_duplicate_files('/path/to/search')
for file_hash, filepaths in duplicates.items():
    print(f"重复文件（哈希: {file_hash[:8]}...）:")
    for path in filepaths:
        print(f"  - {path}")
```

---

## 最佳实践

### 1. 路径处理

```python
# 正确：使用os.path处理路径
path = os.path.join('dir', 'subdir', 'file.txt')

# 错误：硬编码路径分隔符
path = 'dir' + '/' + 'subdir' + '/' + 'file.txt'  # 不可移植
```

### 2. 错误处理

```python
# 正确：使用try-except处理异常
try:
    os.remove('file.txt')
except OSError as e:
    print(f"错误: {e}")

# 错误：不检查返回值
result = os.remove('file.txt')  # 如果失败会抛出异常
```

### 3. 资源管理

```python
# 使用with语句确保资源释放
with open('file.txt', 'r') as f:
    content = f.read()
# 文件会自动关闭

# 处理大量文件时
files = os.listdir('.')
for filename in files[:100]:  # 限制数量
    process_file(filename)
```

### 4. 跨平台兼容性

```python
# 检查操作系统
import platform
import os

system = platform.system()
if system == 'Windows':
    # Windows特定代码
    pass
elif system == 'Linux':
    # Linux特定代码
    pass
elif system == 'Darwin':
    # macOS特定代码
    pass

# 使用跨平台函数
home = os.path.expanduser('~')  # 所有平台都适用
```

### 5. 性能优化

```python
# 批量操作时使用os.scandir而不是os.listdir
# os.scandir更高效，返回DirEntry对象
with os.scandir('.') as entries:
    for entry in entries:
        if entry.is_file():
            print(f"文件: {entry.name}")
        elif entry.is_dir():
            print(f"目录: {entry.name}")

# 避免重复的状态检查
if os.path.exists('file.txt'):
    if os.path.isfile('file.txt'):
        # 文件存在且是文件
        pass
```

### 6. 安全考虑

```python
# 验证用户输入路径
def safe_path(base_dir, user_path):
    """确保路径在指定目录内"""
    # 规范化路径
    full_path = os.path.abspath(
        os.path.join(base_dir, user_path)
    )
    # 检查是否在基础目录内
    if not full_path.startswith(os.path.abspath(base_dir)):
        raise ValueError("路径越界")
    return full_path

# 安全执行系统命令
import subprocess

# 使用参数列表而不是字符串
result = subprocess.run(['ls', '-la'],  # 安全
                       capture_output=True, text=True)

# 不安全
result = os.system('ls -la')  # 可能被注入
```

### 7. 使用`pathlib`（Python 3.4+）

```python
# 现代路径处理
from pathlib import Path

# 更Pythonic的API
path = Path('/home/user') / 'documents' / 'file.txt'

if path.exists():
    print(f"文件大小: {path.stat().st_size}字节")
    
# 遍历目录
for file in Path('.').glob('*.txt'):
    print(file.name)

# 读取文件
content = path.read_text()

# 写入文件
path.write_text('Hello, World!')
```

---

## 常见问题解答

### Q1: `os.remove()`和 `os.unlink()`的区别？
- 两者功能完全相同，`unlink`是Unix系统调用的名称

### Q2: 如何递归删除非空目录？

```python
import shutil
shutil.rmtree('directory')
```

### Q3: 如何跨平台获取临时目录？

```python
import tempfile
temp_dir = tempfile.gettempdir()
```

### Q4: 如何获取文件的创建时间？

- 在Unix系统上，`os.path.getctime()`返回元数据修改时间
    
- 在Windows上，它返回创建时间
    
- 跨平台获取真实的创建时间需要使用平台特定API
    

### Q5: 如何正确处理中文路径？

```python
# 在Windows上可能需要处理编码
path = '中文路径'.encode('gbk')  # Windows GBK编码
# 或使用Unicode路径
path = '中文路径'  # Python 3默认使用Unicode
```

---

## 总结
`os`模块是Python与操作系统交互的瑞士军刀。通过本指南，你应该能够：
1. 处理文件和目录操作
2. 管理路径（跨平台兼容）
3. 执行系统命令和进程管理
4. 访问和修改环境变量
5. 处理文件权限和属性
6. 编写安全、高效的脚本
    
记住，对于复杂的文件操作，考虑使用 `shutil`模块；对于路径处理，Python 3.4+推荐使用 `pathlib`。

**核心原则**：
- 总是使用 `os.path.join()`拼接路径
- 正确处理异常
- 考虑跨平台兼容性
- 遵循最小权限原则
- 使用with语句管理资源

通过合理使用`os`模块，你可以编写强大、可移植的系统管理脚本和工具程序。

---

## See Also

- [[os-path-guide|os.path 模块深度指南]] —— 路径操作的逐函数详解
- [[06-python-stdlib|Python 内建模块]] —— `os` 在标准库速查中的位置
- [[11-python-cli|Python 命令行工具]] —— 脚本入口与 `-m` 运行方式
- [[09-virtual-environments|Python 虚拟环境]] —— `PATH`、`VIRTUAL_ENV` 等环境变量的实际用途
- [[index|Python 笔记目录]]
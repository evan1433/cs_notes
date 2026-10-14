# git

`git init`  

工作区  暂存区   版本库  
工作区(Working Directory):

- 就是你在电脑里能看到的目录,即当前项目目录
- 是我们直接编辑文件的地方

暂存区(Stage/Index):

- 是一个临时存储区域
- 用于存放已经通过git add命令添加的文件修改内容
- 是准备提交到版本库的文件修改内容

版本库(Repository):

- 工作区有一个隐藏目录.git,这个不算工作区,而是Git的版本库
- 版本库中存储了很多东西,其中最重要的就是stage(暂存区)
- 还有Git为我们自动创建的第一个分支master,以及指向master的一个指针叫HEAD
- 通过git commit命令将暂存区的内容提交到当前分支

`git add`      将文件添加到暂存区
`git ls-files`  查看暂存区中的文件

## 实际开发常用命令流程

### 一、项目初始化流程

```bash
# 克隆远程仓库
git clone <仓库地址>
git clone <仓库地址> <目录名>           # 克隆到指定目录
git clone -b <分支名> <仓库地址>       # 克隆指定分支

# 或在现有目录初始化
git init
git remote add origin <仓库地址>       # 添加远程仓库
git pull origin main                   # 拉取远程代码

# 首次推送并关联远程分支
git push -u origin main
```

### 二、日常开发流程

```bash
# 1. 开始工作前，先拉取最新代码
git pull origin main
# 或更安全的做法（推荐）
git fetch origin
git merge origin/main

# 2. 创建新分支进行开发
git checkout -b feature/login
# 或使用新命令
git switch -c feature/login

# 3. 查看当前状态
git status
git status -s                         # 简洁模式

# 4. 添加文件到暂存区
git add <文件名>                      # 添加单个文件
git add .                             # 添加所有修改
git add -A                            # 添加所有文件（包括删除）
git add -u                            # 只添加已跟踪文件的修改
git add *.java                        # 添加所有 .java 文件

# 5. 提交更改
git commit -m "feat: 添加登录功能"
git commit -am "fix: 修复登录bug"     # 跳过暂存区，直接提交已跟踪文件

# 6. 推送到远程
git push origin feature/login
```

### 三、分支管理流程

```bash
# 查看分支
git branch                            # 查看本地分支
git branch -a                         # 查看所有分支（含远程）
git branch -r                         # 只查看远程分支
git branch -vv                         # 查看分支详细信息及关联的远程分支

# 创建分支
git branch <分支名>                   # 创建但不切换
git checkout -b <分支名>              # 创建并切换
git switch -c <分支名>                # 创建并切换（推荐）

# 切换分支
git checkout <分支名>
git switch <分支名>                   # 推荐

# 合并分支
git checkout main                     # 先切换到目标分支
git merge feature/login               # 合并 feature/login 到 main
git merge --no-ff feature/login       # 禁用快进合并，保留分支历史

# 删除分支
git branch -d <分支名>                # 删除已合并的分支
git branch -D <分支名>               # 强制删除分支

# 重命名分支
git branch -m <旧名> <新名>           # 重命名分支
git branch -m <新名>                  # 重命名当前分支

# 推送本地分支到远程
git push -u origin <分支名>           # 首次推送并关联
git push origin --delete <分支名>     # 删除远程分支
```

### 四、代码回退与撤销

```bash
# 撤销工作区修改（未 add）
git checkout -- <文件名>
git restore <文件名>                  # Git 2.23+ 推荐

# 撤销暂存区修改（已 add，未 commit）
git reset HEAD <文件名>
git restore --staged <文件名>         # Git 2.23+ 推荐

# 撤销最近一次提交（保留修改）
git reset --soft HEAD~1               # 撤销 commit，保留暂存区和工作区
git reset --mixed HEAD~1              # 撤销 commit 和 add，保留工作区（默认）
git reset --hard HEAD~1               # 撤销 commit 和 add，删除工作区修改（危险！）

# 修改最近一次提交信息
git commit --amend -m "新的提交信息"
git commit --amend                    # 打开编辑器修改

# 撤销已推送的提交（公共分支慎用）
git revert <commit-hash>              # 创建新提交来撤销指定提交
git revert HEAD                       # 撤销最近一次提交
```

### 五、远程协作流程

```bash
# 查看远程仓库
git remote -v
git remote show origin                # 查看远程仓库详细信息

# 添加/删除远程仓库
git remote add origin <仓库地址>
git remote remove <远程名>
git remote rename <旧名> <新名>

# 修改远程仓库地址
git remote set-url origin <新地址>

# 拉取远程更新
git fetch origin                      # 只拉取，不合并
git fetch --all                       # 拉取所有远程仓库
git pull origin main                  # 拉取并合并
git pull --rebase origin main         # 拉取并变基（保持线性历史）

# 推送代码
git push origin <分支名>
git push -f origin <分支名>           # 强制推送（危险！）
git push --all origin                 # 推送所有分支

# 同步远程已删除的分支
git fetch -p                          # 或 git remote prune origin
```

### 六、暂存工作（Stash）

```bash
# 当需要临时切换分支但不想提交当前修改时使用
git stash                             # 暂存当前修改
git stash save "描述信息"             # 暂存并添加描述
git stash -u                          # 暂存包括未跟踪的文件

# 查看暂存列表
git stash list

# 恢复暂存
git stash pop                         # 恢复最近一次暂存并删除记录
git stash pop stash@{1}               # 恢复指定的暂存
git stash apply                       # 恢复但不删除记录
git stash apply stash@{1}

# 删除暂存
git stash drop stash@{1}              # 删除指定暂存
git stash clear                       # 删除所有暂存

# 查看暂存内容
git stash show                        # 查看暂存概要
git stash show -p                     # 查看暂存详细差异
```

### 七、冲突解决

```bash
# 合并冲突时
git merge feature/login
# 发生冲突后，手动编辑冲突文件，然后：
git add <冲突文件>
git commit -m "merge: 解决合并冲突"

# 放弃合并
git merge --abort

# 变基冲突时
git rebase main
# 解决冲突后：
git add <冲突文件>
git rebase --continue                 # 继续变基
git rebase --abort                    # 放弃变基

# 查看冲突文件
git diff --name-only --diff-filter=U
```

### 八、查看信息

```bash
# 查看提交历史
git log
git log --oneline                     # 单行显示
git log -n 5                          # 最近5条
git log --graph                       # 图形化显示
git log --oneline --graph --all       # 组合使用
git log --author="张三"               # 按作者筛选
git log --since="2024-01-01"          # 按时间筛选
git log -p <文件名>                   # 查看某文件的修改历史

# 查看差异
git diff                              # 工作区 vs 暂存区
git diff --staged                     # 暂存区 vs 最新提交
git diff HEAD                         # 工作区 vs 最新提交
git diff <分支1> <分支2>              # 比较两个分支
git diff <commit1> <commit2>          # 比较两个提交

# 查看文件内容
git show <commit-hash>                # 查看某次提交的内容
git show <commit-hash>:<文件路径>     # 查看某次提交中某文件的内容

# 查看文件修改历史
git blame <文件名>                    # 显示每行的修改者和时间

# 查看操作记录
git reflog                            # 查看所有操作记录，可用于恢复误删
```

### 九、实用技巧

```bash
# 选择性合并某次提交
git cherry-pick <commit-hash>

# 清理未跟踪的文件
git clean -n                          # 预览要删除的文件
git clean -f                          # 删除未跟踪的文件
git clean -fd                         # 删除未跟踪的文件和目录

# 二分查找定位问题
git bisect start
git bisect bad                        # 当前版本有问题
git bisect good <commit-hash>         # 这个版本没问题
# Git 会自动定位到引入问题的提交

# 查看某行代码的修改历史
git log -L 10,20:file.txt             # 查看文件第10-20行的修改历史

# 只克隆最近一次提交（节省空间和时间）
git clone --depth 1 <仓库地址>

# 更新子模块
git submodule update --init --recursive
```

### 十、提交信息规范（约定式提交）

```bash
# 常用提交类型
feat:     新功能
fix:      修复 bug
docs:     文档更新
style:    代码格式（不影响功能）
refactor: 重构（不是新功能也不是修复 bug）
test:     添加测试
chore:    构建过程或辅助工具的变动

# 示例
git commit -m "feat: 添加用户登录功能"
git commit -m "fix: 修复登录页面样式问题"
git commit -m "docs: 更新 README 文档"
git commit -m "refactor: 重构用户模块代码结构"
```

`git rm  filename`    把文件从工作区和暂存区同时删除
`git rm --cached filename`  把文件从暂存区删除，但保留在当前工作区中
`git rm -r *`  递归删除某个目录下的所有子目录和文件
删除后不要忘记提交

## git commit

`git commit -m "xxx"`  提交说明
`git commit --amend`    修改先前的提交

## git reset

| 选项 | 作用|
|------|------|
|--soft| 保留工作区和暂存区      |
|--hard| 删除工作区和暂存区    |
|--mixed| 保留工作区，删除暂存区 |

## git diff

一般用图形化工具

[git diff 命令](https://blog.csdn.net/liuxiao723846/article/details/109689069)

## git push

`git push <远程仓库名> <本地分支名>:<远程分支名>` 用于将本地分支的更新推送到远程仓库。
如果本地分支名和远程分支名相同，可以省略 `:<远程分支名>` 部分。例如 `git push origin main`。
`git push -u <远程仓库名> <本地分支名>` 首次推送时使用，`-u` 选项会将本地分支和远程分支关联起来，之后使用 `git push` 就可以直接推送。

## git pull

`git pull <远程仓库名> <远程分支名>` 用于从远程仓库拉取指定分支的更新，并尝试自动合并到当前本地分支。它实际上是 `git fetch` 和 `git merge` 的组合。如果本地分支已经和远程分支关联，可直接使用 `git pull`。

## git status

`git status` 用于查看工作区、暂存区的状态。它会显示哪些文件被修改但未暂存，哪些文件已暂存但未提交等信息。  
`git status -s` 可以以简洁模式显示状态信息。

## git log

`git log` 用于查看提交历史记录。
`git log --oneline` 可以将每条提交记录显示在一行，使输出更简洁。
`git log -n <数量>` 可以只显示最近的 `<数量>` 条提交记录。
`git log --graph` 可以以图形化的方式显示提交历史，便于查看分支合并情况。

## git merge

`git merge <分支名>` 用于将指定分支的修改合并到当前分支。

合并有两种常见情况：快进合并（Fast-forward）和三方合并（Three-way merge）。如果合并过程中出现冲突，需要手动解决冲突后再提交。`git merge --abort` 可以在合并冲突时放弃合并操作，回到合并前的状态。

`git merge feature`   将 feature 分支合并到当前分支

## git worktree

`git worktree` 用于在同一仓库下同时检出多个分支到不同目录，共享同一份对象库，避免来回 `stash` 切换分支。适合紧急 hotfix、并行开发、版本对比等场景。完整用法见 [[git-worktree|Git Worktree 多工作树使用指南]]。

## git  rebase

将一个分支的提交历史“重新定位”到另一个分支的最新提交上，从而形成线性的提交历史。

## git checkout

`git checkout -b <新分支名>` 用于创建并切换到一个新的分支。
例如，`git checkout -b feature` 会创建一个名为 `feature` 的新分支，并立即切换到该分支。

`git checkout <分支名>` 用于切换到已有的分支。例如，`git checkout main` 会切换到 `main` 分支。

`git checkout <提交哈希值>` 用于切换到指定的提交，此时会处于“分离头指针”状态。在这种状态下的修改不会影响任何分支，除非创建新分支来保存这些修改。

## git switch

`git switch -c <新分支名>` 功能与 `git checkout -b` 类似，用于创建并切换到一个新的分支。
例如，`git switch -c bugfix` 会创建一个名为 `bugfix` 的新分支，并切换到该分支。

`git switch <分支名>` 用于切换到已有的分支，与 `git checkout <分支名>` 功能相同。
例如，`git switch develop` 会切换到 `develop` 分支。

`git switch` 是 Git 2.23 版本引入的新命令，旨在提供更清晰的分支切换操作，与 `git checkout` 相比，`git switch` 更专注于分支切换，而 `git checkout` 还可用于恢复文件等操作。

## git branch

`git branch` 用于列出本地所有分支，当前所在分支会用 `*` 标记。

`git branch <新分支名>` 用于创建一个新的分支，但不会切换到该分支。例如，`git branch experimental` 会创建一个名为 `experimental` 的新分支。

`git branch -d <分支名>` 用于删除已经合并到当前分支的指定分支。如果分支还有未合并的更改，使用该命令会失败，可使用 `git branch -D <分支名>` 强制删除。

`git branch -m <旧分支名> <新分支名>` 用于重命名本地分支。例如，`git branch -m old-name new-name` 会将 `old-name` 分支重命名为 `new-name`。

`git clone -b barnch-name`  克隆指定分支

## git remote

```
git remote -v   查看git远程仓库地址
git remote set-url origin 新地址    替换成新地址
```

## tag 打标签

Git 标签（Tag）是用于标记特定提交的引用，通常用于标记版本发布（如 v1.0、v2.0）。标签一旦创建就永远不会变化，适合用于记录项目的重要里程碑。

### 标签的类型

| 类型 | 说明 | 用途 |
|------|------|------|
| **轻量级标签（Lightweight Tag）** | 不可添加注释，只是指向某次提交的引用 | 私人或临时对象标记 |
| **带附注标签（Annotated Tag）** | 可添加注释，包含标签信息（注释、打标签者、时间等） | 用于正式发布版本 |

**推荐使用带附注标签**，因为它包含更多信息，更适合正式版本发布。

### 创建标签

#### 创建轻量级标签

```bash
# 为当前提交创建轻量级标签
git tag v1.0

# 为指定提交创建轻量级标签
git tag v0.9 commitId
```

#### 创建带附注标签

```bash
# 为当前提交创建带附注标签
git tag -a v1.0 -m "版本 1.0 发布"

# 为指定提交创建带附注标签
git tag -a v0.9 commitId -m "版本 0.9 发布"
```

**参数说明**：
- `-a`：创建带附注标签（annotated）
- `-m`：添加标签注释信息
- `commitId`：指定为哪次提交打标签（可选，默认为当前提交）

### 查看标签

#### 显示所有标签

```bash
# 显示所有标签
git tag

# 或使用 list 选项
git tag --list
```

#### 查看标签详细信息

```bash
# 查看标签详细信息
git show v1.0
```

**输出内容**：
- **轻量级标签**：显示指向的提交信息（提交哈希、作者、日期、提交信息）
- **带附注标签**：显示标签对象信息（标签名称、注释、打标签者、时间）+ 提交信息

### 查找标签

支持使用通配符和正则表达式查找标签：

```bash
# 查找以 v 开头的标签
git tag -l "v*"

# 查找包含 2 的标签
git tag -l "*2*"

# 查找 v1.x 版本的标签
git tag -l "v1.*"

# 查找特定模式的标签
git tag -l "?2*"  # 第二个字符是 2 的标签
```

### 推送标签到远程

标签默认不会推送到远程仓库，需要手动推送。

#### 推送指定标签

```bash
# 推送单个标签到远程
git push origin v1.0

# 推送多个标签到远程
git push origin v1.0 v2.0 v3.0

# 完整写法（推送标签引用）
git push origin refs/tags/v1.0:refs/tags/v1.0
```

#### 推送所有本地标签

```bash
# 推送所有本地标签到远程
git push origin --tags

# 或简写
git push --tags
```

**注意**：推送所有标签时，轻量级标签和带附注标签都会被推送。

### 删除标签

#### 删除本地标签

```bash
# 删除本地标签
git tag -d v1.0

# 删除多个本地标签
git tag -d v0.9 v1.0
```

#### 删除远程标签

```bash
# 方法一：推送空标签引用（删除远程标签）
git push origin :v1.0
# 完整写法
git push origin :refs/tags/v1.0

# 方法二：使用 delete 参数（推荐）
git push origin --delete v1.0
# 完整写法
git push origin --delete tag v1.0
```

**删除流程**：
1. 先删除本地标签：`git tag -d v1.0`
2. 再删除远程标签：`git push origin --delete v1.0`

### 切换标签

```bash
# 切换到指定标签
git checkout v1.0

# 切换标签并创建新分支（推荐）
git checkout -b version1 v1.0
```

**注意**：
- 切换标签会使 HEAD 处于游离状态（detached HEAD）
- 在游离状态下修改不会被任何分支记录
- 如需修改，建议创建新分支保存修改

### 拉取标签

#### 拉取远程标签

```bash
# 拉取远程仓库所有标签
git fetch --all --tags

# 或使用 pull（会拉取提交和标签）
git pull
```

**拉取行为**：
- 当本地与远程仓库有公共提交历史且无冲突时，`git pull` 会将远程仓库的标签拉取到本地
- 拉取的标签会在本地创建相应的本地标签

#### 查看远程标签

```bash
# 查看远程仓库的标签
git ls-remote --tags origin
```

### 标签使用场景

#### 1. 版本发布

在 master 分支成熟阶段打标签，标记版本发布：

```bash
# 发布新版本
git tag -a v1.0 -m "正式版本 1.0 发布"
git push origin v1.0

# 发布补丁版本
git tag -a v1.0.1 -m "修复 bug #123"
git push origin v1.0.1

# 发布新功能版本
git tag -a v1.1 -m "新增用户管理功能"
git push origin v1.1
```

#### 2. 版本管理

记录项目某一阶段的状态，便于管理和回溯：

```bash
# 标记开发阶段
git tag -a alpha-1.0 -m "Alpha 测试版本"
git tag -a beta-1.0 -m "Beta 测试版本"
git tag -a rc-1.0 -m "Release Candidate"

# 标记重要里程碑
git tag -a milestone-1 -m "完成核心功能开发"
```

#### 3. 回溯历史版本

```bash
# 查看历史版本
git checkout v0.9

# 对比版本差异
git diff v0.9 v1.0

# 查看版本间的提交历史
git log v0.9..v1.0
```

### 标签命名规范

#### 版本号命名规范（语义化版本）

遵循语义化版本规范（Semantic Versioning）：`MAJOR.MINOR.PATCH`

- **MAJOR**：主版本号（不兼容的 API 修改）
- **MINOR**：次版本号（向后兼容的功能新增）
- **PATCH**：修订号（向后兼容的问题修复）

**示例**：

```bash
# 主版本更新（重大变更）
v1.0.0 -> v2.0.0

# 次版本更新（新功能）
v1.0.0 -> v1.1.0

# 修订版本更新（bug 修复）
v1.0.0 -> v1.0.1

# 预发布版本
v1.0.0-alpha
v1.0.0-beta
v1.0.0-rc.1
```

#### 其他命名规范

```bash
# 按日期命名
release-2024-01-01
release-2024-q1

# 按阶段命名
alpha-v1.0
beta-v1.0
rc-v1.0
stable-v1.0

# 按功能命名
feature-login-v1.0
hotfix-security-v1.0.1
```

### 标签最佳实践

1. **使用带附注标签**：包含更多信息，更适合正式版本发布

```bash
git tag -a v1.0 -m "版本 1.0 发布说明"
```

2. **遵循语义化版本规范**：便于版本管理和理解

```bash
v1.0.0  # 主版本.次版本.修订版本
```

3. **在稳定分支打标签**：通常在 master 或 main 分支打标签

```bash
git checkout main
git tag -a v1.0 -m "正式版本发布"
```

4. **及时推送标签**：打标签后及时推送到远程仓库

```bash
git push origin v1.0
```

5. **标签信息完整**：带附注标签应包含版本说明、变更内容等

```bash
git tag -a v1.0 -m "版本 1.0 发布
新增功能：
- 用户登录
- 权限管理

修复问题：
- bug #123
- bug #456
"
```

6. **避免频繁删除标签**：标签是版本记录，应避免频繁删除

### 标签相关命令速查表

| 操作 | 命令 |
|------|------|
| 创建轻量级标签 | `git tag <标签名>` |
| 创建带附注标签 | `git tag -a <标签名> -m "注释"` |
| 为指定提交打标签 | `git tag <标签名> <commitId>` |
| 显示所有标签 | `git tag` |
| 查看标签详细信息 | `git show <标签名>` |
| 查找标签 | `git tag -l "模式"` |
| 推送单个标签 | `git push origin <标签名>` |
| 推送所有标签 | `git push origin --tags` |
| 删除本地标签 | `git tag -d <标签名>` |
| 删除远程标签 | `git push origin --delete <标签名>` |
| 切换标签 | `git checkout <标签名>` |
| 切换标签并创建分支 | `git checkout -b <分支名> <标签名>` |
| 拉取远程标签 | `git fetch --all --tags` |
| 查看远程标签 | `git ls-remote --tags origin` |

### 参考资料

- [创建标签 - 廖雪峰](https://liaoxuefeng.com/books/git/tag/create/index.html)
- [操作标签 - 廖雪峰](https://liaoxuefeng.com/books/git/tag/push-delete/index.html)
- [Git应用详解第八讲：Git标签、别名与Git gc](https://blog.csdn.net/weixin_39642619/article/details/111223447)
- [Git标签管理](https://blog.csdn.net/lovedingd/article/details/127568704)
- [Git tag 使用详解](https://blog.csdn.net/weixin_43715214/article/details/131059079)
- [How to checkout git tags](https://devconnected.com/how-to-checkout-git-tags/)

## config

- 免密拉取   `git config --global credential.helper store`
- 关闭ca认证  `sudo git config --system http.sslverify false`
- `git config --global http.sslverify false`

```shell
git config --local --list
git config --local user.name dukechase
git config --local user.email  hsb2435@163.com
```

## [Git 多用户配置](https://www.cnblogs.com/cangqinglang/p/12462272.html)

### 各部分含义

1. **`Host gitee`**
    - 定义了一个别名 `gitee`，表示你可以通过这个别名来简化对 Gitee 的连接。
    - 当你在命令行中使用 `ssh gitee` 或与 Gitee 相关的 Git 操作时，SSH 客户端会根据这个别名查找对应的配置。
2. **`HostName gitee.com`**
    - 指定了实际的目标主机地址，这里是 `gitee.com`。
    - 当你使用别名 `gitee` 时，SSH 客户端会将它解析为 `gitee.com`。
3. **`Port 22`**
    - 指定了连接到目标主机时使用的端口号，默认情况下，SSH 使用的是 22 端口。
    - 如果 Gitee 使用非标准端口，则可以在这里修改为其他值。
4. **`IdentityFile ~/.ssh/gitee_id_rsa`**
    - 指定了用于身份验证的私钥文件路径。
    - 在这里，`~/.ssh/gitee_id_rsa` 是一个私钥文件，SSH 客户端会用它来验证你的身份，以便成功连接到 Gitee。

```text
Host github
HostName github.com
IdentityFile ~/.ssh/id_rsa_github

Host gitlab
HostName gitlab.mygitlab.com
IdentityFile ~/.ssh/id_rsa_gitlab
```

测试连接

```bash
ssh -T git@github
Hi jitwxs! You've successfully authenticated, but GitHub does not provide shell access.
```

```bash
ssh -T git@gitlab
Welcome to GitLab, @lemon!
```

## gitignore

`.gitignore` 文件用于指定 Git 应该忽略的文件和目录，即这些文件不会被纳入版本控制。

以下是 `.gitignore` 文件的常见规则：

### 1. 基本语法

- **忽略文件**：直接写上文件名，每行一个。例如：

```ignore
temp.txt
```

这会忽略项目根目录下的 `temp.txt` 文件。

- **忽略目录**：在目录名后加斜杠 `/`。例如：

```ignore
logs/
```

这会忽略项目根目录下的 `logs` 目录及其所有内容。

### 2. 通配符使用

- `*`：匹配任意数量的任意字符。例如：

```ignore
*.log
```

这会忽略所有扩展名为 `.log` 的文件。

- `?`：匹配单个任意字符。例如：

```ignore
file?.txt
```

这会忽略 `file1.txt`、`fileA.txt` 等文件。

- `[abc]`：匹配方括号内的任意一个字符。例如：

```ignore
file[123].txt
```

这会忽略 `file1.txt`、`file2.txt` 和 `file3.txt`。

### 3. 递归匹配

如果没有指定路径，规则会递归应用到整个项目。例如：

```ignore
*.tmp
```

这会忽略项目中所有扩展名为 `.tmp` 的文件，无论它们在哪个目录下。

### 4. 否定规则

在规则前加 `!` 可以取消之前的忽略规则。例如：

```ignore
*.log
!important.log
```

这会忽略所有 `.log` 文件，但 `important.log` 文件除外。

### 5. 注释

以 `#` 开头的行是注释，会被 Git 忽略。例如：

```ignore
# 忽略临时文件
*.tmp
```

### 6. 路径匹配

可以使用相对路径指定要忽略的文件或目录。例如：

```ignore
src/test/results/
```

这会忽略 `src/test/results` 目录及其所有内容。 



- [git 子模块](https://git-scm.com/book/zh/v2/Git-%E5%B7%A5%E5%85%B7-%E5%AD%90%E6%A8%A1%E5%9D%97)

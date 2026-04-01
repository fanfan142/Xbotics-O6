# 上传到 GitHub 指南

## 方法一：命令行（推荐）

### 1. 在 GitHub 创建仓库

1. 打开 https://github.com/new
2. Repository name 填写：`xbotics-o6`
3. Description 填写：`基于 MediaPipe 手势识别与 O6 灵巧手的实时控制系统`
4. 选择 Public 或 Private
5. **不要勾选** "Add a README file"
6. 点击 "Create repository"

### 2. 本地初始化并推送

打开命令行，进入 xbotics3 目录执行：

```bash
cd F:\sim\灵心巧手\o6\o6_student_minipack\xbotics3

# 初始化 Git（如果是全新仓库）
git init

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit: Xbotics O6 Control Console"

# 重命名默认分支为 main
git branch -M main

# 添加远程仓库（替换 YOUR_USERNAME 为你的 GitHub 用户名）
git remote add origin https://github.com/YOUR_USERNAME/xbotics-o6.git

# 推送
git push -u origin main
```

### 3. 以后更新代码

```bash
git add .
git commit -m "Your commit message"
git push
```

---

## 方法二：GitHub Desktop

### 1. 下载 GitHub Desktop

https://desktop.github.com/

### 2. 添加本地仓库

1. File → Add Local Repository
2. 浏览选择 `F:\sim\灵心巧手\o6\o6_student_minipack\xbotics3`
3. 点击 "Add Repository"

### 3. 发布到 GitHub

1. 点击 "Publish repository"
2. 填写仓库名称和描述
3. 选择 Private 或 Public
4. 点击 "Publish repository"

---

## 方法三：网页直接上传

### 1. 创建空仓库

1. 打开 https://github.com/new
2. 填写仓库名等信息，创建空仓库

### 2. 通过网页上传

1. 在新建的仓库页面，点击 "uploading an existing file"
2. 拖拽所有文件到上传区域
3. 点击 "Commit changes"

---

## 首次配置 Git（如果没用过）

```bash
# 设置用户名和邮箱
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

---

## 如果遇到问题

**Q: git remote add origin 报错 "remote origin already exists"**
```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/xbotics-o6.git
```

**Q: git push 需要输入用户名密码**
建议使用 Personal Access Token 或配置 SSH Key。

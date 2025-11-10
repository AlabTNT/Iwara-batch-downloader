# Iwara-batch-downloader
A downloader for batch download videos from iwara.tv by using .txt and bookmarks

## 简介
本脚本用于批量或单个保存 iwara.tv 的视频，仅需提供链接。目前仅支持 Windows 平台。

## 使用方法
1. 下载本 repo 的 .zip 副本并解压缩
2. 在文件夹下执行 `pip install -r requirements.txt`
3. 运行 `python iwara.py`
4. 根据提示继续

## 书签与 .txt 使用方法
### 如何使用书签？
目前仅测试过 Microsoft Edge 和 Chrome 的书签，不保证其他浏览器一定可以运行。

1. 首先，在 Iwara 上找到您喜欢的视频，然后打开它。尽量使用 Ctrl + 单击 的方式打开而不进入标签页，这样可以继续使用搜索或主页浏览其他您喜欢的视频。  
2. 当您找完视频后，使用 Ctrl + Shift + D 保存当前窗口所有标签页到收藏夹。  
3. 按下 Ctrl + Shift + O 打开收藏夹/书签管理器，点击更多（图标为三个点），选择导出书签，将书签/收藏夹全部导出到本 repo 解压后的文件夹内。  
4. 执行本脚本即可自动识别吸收书签/收藏夹。

### 如何使用 .txt？
1. 创建任意名称的 .txt 文件到本 repo 解压后的文件夹内。
2. 复制您喜欢的 Iwara 视频的链接，然后按行粘贴到 .txt 文件中，每行一个 Iwara 视频链接。
3. 保存 .txt 文件
4. 执行本脚本即可自动识别 .txt 文件

## 声明
本脚本仅用于交流学习，创作者本人不承担任何由此脚本引发的版权纠纷问题。有关视频内容，一切权利归 Iwara.tv 与视频创作者所有。

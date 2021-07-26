# -*- coding:utf-8 -*-
import wx
import requests
from requests.packages import urllib3
from datetime import datetime


def main(api_key, youtube_channel_id, startTime, endTime):
    startTime = datetime.strptime(startTime, '%Y-%m-%d')
    endTime = datetime.strptime(endTime, '%Y-%m-%d')
    youtube_spider = YoutubeSpider(api_key)
    uploads_id, subscriber = youtube_spider.get_channel_uploads_id(youtube_channel_id)
    message = dict()

    next_page_token = ''
    views = 0
    count = 0
    likes = 0
    comments = 0
    page_count = 0
    while 1:
        video_ids, next_page_token = youtube_spider.get_playlist(uploads_id, max_results=50, page_token=next_page_token)
        print(len(video_ids))
        for video_id in video_ids:
            video_info = youtube_spider.get_video(video_id)
            if endTime > video_info['publishedAt'] > startTime:
                print(video_info['title'], ":", video_info['viewCount'], "Published at : ", video_info['publishedAt'])
                views += int(video_info['viewCount'])
                likes += int(video_info['likeCount'])
                comments += int(video_info['commentCount'])
                count += 1
            else:
                if count >= 1:
                    message["统计的视频数量"] = count
                    message["平均播放量"] = "%.2f%%" % (views / count)
                    message["点赞量/播放次数"] = "%.2f%%" % (likes / views * 100)
                    message["评论数/播放次数"] = "%.2f%%" % (comments / views * 100)
                    message["粉丝数"] = int(subscriber)
                    message["平均播放量/粉丝数"] = "%.2f%%" % (views / count / int(subscriber) * 100)
                    break
                else:
                    continue
        if page_count == count:
            break
        else:
            page_count = count
        if not next_page_token:
            break
    return message


class YoutubeSpider():
    def __init__(self, api_key):
        self.base_url = "https://www.googleapis.com/youtube/v3/"
        self.api_key = api_key

    def get_html_to_json(self, path):
        """组合 URL 后 GET 网页并转换成 JSON"""
        api_url = f"{self.base_url}{path}&key={self.api_key}"
        urllib3.disable_warnings()
        r = requests.get(api_url, verify=False)
        if r.status_code == requests.codes.ok:
            data = r.json()
        else:
            data = None
        return data

    def get_channel_uploads_id(self, channel_id, part='contentDetails%2Cstatistics'):
        """取得频道上传视频的ID"""
        # UC7ia-A8gma8qcdC6GDcjwsQ
        path = f'channels?part={part}&id={channel_id}'
        data = self.get_html_to_json(path)
        try:
            uploads_id = data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            subscriber = data['items'][0]['statistics']['subscriberCount']
        except KeyError:
            uploads_id = None
            subscriber = None
        return uploads_id, subscriber

    def get_playlist(self, playlist_id, part='contentDetails', max_results=10, page_token=''):
        """取得视频清单ID中的视频"""
        # UU7ia-A8gma8qcdC6GDcjwsQ
        path = f'playlistItems?part={part}&playlistId={playlist_id}&maxResults={max_results}&pageToken={page_token}'
        data = self.get_html_to_json(path)
        if not data:
            return []
        next_page_token = data.get('nextPageToken', '')

        video_ids = []
        for data_item in data['items']:
            video_ids.append(data_item['contentDetails']['videoId'])
        return video_ids, next_page_token

    def get_video(self, video_id, part='snippet,statistics'):
        """取得影片详情"""
        # jyordOSr4cI
        # part = 'contentDetails,id,liveStreamingDetails,localizations,player,recordingDetails,snippet,statistics,status,topicDetails'
        path = f'videos?part={part}&id={video_id}'
        data = self.get_html_to_json(path)
        if not data:
            return {}
        # 以下整理并提取需要的资料
        data_item = data['items'][0]

        try:
            # 2019-09-29T04:17:05Z
            time_ = datetime.strptime(data_item['snippet']['publishedAt'], '%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            # 日期格式错误
            time_ = None

        url_ = f"https://www.youtube.com/watch?v={data_item['id']}"

        info = {
            'id': data_item['id'],
            'channelTitle': data_item['snippet']['channelTitle'],
            'publishedAt': time_,
            'video_url': url_,
            'title': data_item['snippet']['title'],
            'description': data_item['snippet']['description'],
            'likeCount': data_item['statistics']['likeCount'],
            'dislikeCount': data_item['statistics']['dislikeCount'],
            'commentCount': data_item['statistics']['commentCount'],
            'viewCount': data_item['statistics']['viewCount']
        }
        return info

    def get_comments(self, video_id, page_token='', part='snippet', max_results=100):
        """取得视频留言"""
        # jyordOSr4cI
        path = f'commentThreads?part={part}&videoId={video_id}&maxResults={max_results}&pageToken={page_token}'
        data = self.get_html_to_json(path)
        if not data:
            return [], ''
        # 下一页的数值
        next_page_token = data.get('nextPageToken', '')

        # 以下整理并提取需要的资料
        comments = []
        for data_item in data['items']:
            data_item = data_item['snippet']
            top_comment = data_item['topLevelComment']
            try:
                # 2020-08-03T16:00:56Z
                time_ = datetime.strptime(top_comment['snippet']['publishedAt'], '%Y-%m-%dT%H:%M:%SZ')
            except ValueError:
                # 日期格式错误
                time_ = None

            if 'authorChannelId' in top_comment['snippet']:
                ru_id = top_comment['snippet']['authorChannelId']['value']
            else:
                ru_id = ''

            ru_name = top_comment['snippet'].get('authorDisplayName', '')
            if not ru_name:
                ru_name = ''

            comments.append({
                'reply_id': top_comment['id'],
                'ru_id': ru_id,
                'ru_name': ru_name,
                'reply_time': time_,
                'reply_content': top_comment['snippet']['textOriginal'],
                'rm_positive': int(top_comment['snippet']['likeCount']),
                'rn_comment': int(data_item['totalReplyCount'])
            })
        return comments, next_page_token


class MyFrame(wx.Frame):
    def __init__(self,  parent,  id):
        wx.Frame.__init__(self,  parent,  id,  '播放信息查询',  size=(400,  300))
        # 创建面板
        panel = wx.Panel(self)

        # 创建“确定”和“取消”按钮, 并绑定事件
        self.bt_confirm = wx.Button(panel,  label='确定')
        self.bt_confirm.Bind(wx.EVT_BUTTON, self.OnclickSubmit)
        self.bt_cancel = wx.Button(panel,  label='取消')
        self.bt_cancel.Bind(wx.EVT_BUTTON, self.OnclickCancel)
        # 创建文本，左对齐
        self.title = wx.StaticText(panel,  label="请输入查询信息")
        self.api_key = wx.StaticText(panel,  label="YoutubeAPI Key:")
        self.text_key = wx.TextCtrl(panel,  style=wx.TE_PASSWORD)
        self.channel_id = wx.StaticText(panel,  label="Channel ID:")
        self.text_channel = wx.TextCtrl(panel,  style=wx.TE_LEFT)
        self.start_time = wx.StaticText(panel,  label="起始时间(YYYY-MM-DD):")
        self.text_start = wx.TextCtrl(panel,  style=wx.TE_LEFT)
        self.end_time = wx.StaticText(panel,  label="终止时间(YYYY-MM-DD):")
        self.text_end = wx.TextCtrl(panel,  style=wx.TE_LEFT)
        # 添加容器，容器中控件按横向并排排列
        hsizer_key = wx.BoxSizer(wx.HORIZONTAL)
        hsizer_key.Add(self.api_key,  proportion=0,  flag=wx.ALL,  border=5)
        hsizer_key.Add(self.text_key,  proportion=1,  flag=wx.ALL,  border=5)
        hsizer_channel = wx.BoxSizer(wx.HORIZONTAL)
        hsizer_channel.Add(self.channel_id,  proportion=0,  flag=wx.ALL,  border=5)
        hsizer_channel.Add(self.text_channel,  proportion=1,  flag=wx.ALL,  border=5)
        hsizer_startTime = wx.BoxSizer(wx.HORIZONTAL)
        hsizer_startTime.Add(self.start_time,  proportion=0,  flag=wx.ALL,  border=5)
        hsizer_startTime.Add(self.text_start,  proportion=1,  flag=wx.ALL,  border=5)
        hsizer_endTime = wx.BoxSizer(wx.HORIZONTAL)
        hsizer_endTime.Add(self.end_time,  proportion=0,  flag=wx.ALL,  border=5)
        hsizer_endTime.Add(self.text_end,  proportion=1,  flag=wx.ALL,  border=5)
        hsizer_button = wx.BoxSizer(wx.HORIZONTAL)
        hsizer_button.Add(self.bt_confirm,  proportion=0,  flag=wx.ALIGN_CENTER,  border=5)
        hsizer_button.Add(self.bt_cancel,  proportion=0,  flag=wx.ALIGN_CENTER,  border=5)
        # 添加容器，容器中控件按纵向并排排列
        vsizer_all = wx.BoxSizer(wx.VERTICAL)
        vsizer_all.Add(self.title,  proportion=0,  flag=wx.BOTTOM | wx.TOP | wx.ALIGN_CENTER,
                        border=15)
        vsizer_all.Add(hsizer_key,  proportion=0,  flag=wx.EXPAND | wx.LEFT | wx.RIGHT,  border=45)
        vsizer_all.Add(hsizer_channel,  proportion=0,  flag=wx.EXPAND | wx.LEFT | wx.RIGHT,  border=45)
        vsizer_all.Add(hsizer_startTime, proportion=0, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=45)
        vsizer_all.Add(hsizer_endTime, proportion=0, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=45)
        vsizer_all.Add(hsizer_button,  proportion=0,  flag=wx.ALIGN_CENTER | wx.TOP,  border=15)
        panel.SetSizer(vsizer_all)

    def OnclickSubmit(self, event):
        """ 点击确定按钮，执行方法 """
        message = ""

        api_key = self.text_key.GetValue().strip()
        channel_id = self.text_channel.GetValue().strip()
        start_time = self.text_start.GetValue().strip()
        end_time = self.text_end.GetValue().strip()

        if api_key == "" or channel_id == "" or start_time == "" or end_time == "":
            message = '必填项不能为空'
        else:
            message_dict = main(api_key, channel_id, start_time, end_time)
            for key, value in message_dict.items():
                message = message + key + " : " + str(value) + "\n"
        wx.MessageBox(message, caption="查询结果", style=wx.OK)                        # 弹出提示框

    def OnclickCancel(self, event):  # 没有event点击取消会报错
        """ 点击取消按钮，执行方法 """
        self.text_key.SetValue("")
        self.text_channel.SetValue("")
        self.text_start.SetValue("")
        self.text_end.SetValue("")

if __name__ == '__main__':
    app = wx.App()                      # 初始化
    frame = MyFrame(parent=None, id=-1)  # 实例MyFrame类，并传递参数
    frame.Show()                        # 显示窗口
    app.MainLoop()                      # 调用主循环方法

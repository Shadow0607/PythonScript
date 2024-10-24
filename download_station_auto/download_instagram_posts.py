import instaloader
from instaloader import Profile
from datetime import datetime, timezone, timedelta
import pytz

USERNAME = '123'  # 请替换为您的 Instagram 用户名
PASSWORD = '132'  # 请替换为您的 Instagram 密码


# 用户名列表
usernames = ['tanbowgo', 'yyyoungggggg','yoona__lim'] 

# 置顶帖子 shortcodes 列表，手动管理
pinned_posts_shortcodes = ['CyuHEuByfGC', 'C5Cx99XyY9y','Cf3TbJKPQbv','DA1Q00bysBX']

def print_post_info(post):
    print("\n帖子详细信息：")
    print(f"  ID: {post.shortcode}")
    print(f"  发布时间 (本地时间): {post.date_local}")
    print(f"  发布时间 (UTC): {post.date_utc}")
    print(f"  类型: {'视频' if post.is_video else '图片'}")
    print(f"  是否被钉选: {'是' if hasattr(post, 'is_pinned') and post.is_pinned else '否'}")

def main():
    L = instaloader.Instaloader(download_videos=True,
    download_video_thumbnails=True,
    download_comments=False,
    save_metadata=False,
    post_metadata_txt_pattern='',  # 不保存描述文件
    storyitem_metadata_txt_pattern='',
    dirname_pattern=r'C:\Users\123\Desktop\ig'
    )
    days_to_fetch = 3  # 你可以修改这个值来设置要抓取的天数
    until = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    since = (until - timedelta(days=days_to_fetch)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 确保 since 和 until 都带有时区信息
    taiwan_tz = pytz.timezone('Asia/Taipei')
    since = taiwan_tz.localize(since)
    until = taiwan_tz.localize(until)
    
    # 使用会话cookie登录
    try:
        L.login(USERNAME, PASSWORD)
        L.save_session_to_file()
        L.load_session_from_file(USERNAME)
        print("会话加载成功。")
    except FileNotFoundError:
        print("未找到会话文件，尝试通过用户名和密码登录。")
        L.context.log("正在通过用户名和密码登录...")
        L.login(USERNAME, PASSWORD)
        L.save_session_to_file()
        print("会话已保存。")

    print(f"当前台湾时间：{datetime.now(timezone(timedelta(hours=8)))}")
    print(f"起始时间（since）：{since}")
    print(f"结束时间（until）：{until}")

    for username in usernames:
        print(f"\n正在搜索 {username} 的帖子，时间范围：{since} 到 {until} ...")
        try:
            profile = Profile.from_username(L.context, username)
        except instaloader.exceptions.ProfileNotExistsException:
            print(f"用户 {username} 不存在。")
            continue
        except Exception as e:
            print(f"获取用户 {username} 时出错：{e}")
            continue

        posts = profile.get_posts()
        
        found_posts = False
        post_count = 0  # 初始化计数器
        for post in posts:
            #if post_count < 3:
            #    post_count += 1
            #    continue  # 跳过前3篇帖子
            if post.shortcode in pinned_posts_shortcodes:
                print(f"跳过已知的置顶帖子：{post.shortcode}")
                continue

            post_date = post.date_local.astimezone(timezone(timedelta(hours=8)))
            print_post_info(post)

            if since <= post_date <= until:
                print("  状态：符合条件，准备下载")
                found_posts = True
                try:
                    L.download_post(post, target=f"{username}_posts")
                    print("  状态：已下载帖子")
                except Exception as e:
                    print(f"  状态：下载帖子时出错：{e}")
            elif post_date < since:
                print(f"  状态：非钉选帖子早于 'since' {since}，停止搜索")
                break
            else:
                print("  状态：不在指定时间范围内，跳过")

        if not found_posts:
            print(f"{username} 在指定的时间范围内没有非钉选的帖子。")

    print("\n所有用户的帖子处理完成。")

if __name__ == "__main__":
    main()
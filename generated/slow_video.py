from moviepy.editor import VideoFileClip

clip = VideoFileClip("final_video-4.mp4")
slow = clip.fx(vfx.speedx, 0.1)   # 0.1x = tenth speed
slow.write_videofile("slow_output.mp4")
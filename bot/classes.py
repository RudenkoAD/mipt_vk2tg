class Link:
    vk_id:int
    tg_id:int
    last_post:int
    def __init__(self, vkid:int, tgid:int, userid:int, postid:int=None) -> None:
        self.vk_id = vkid
        self.tg_id = tgid
        self.post_id = postid
        self.user_id = userid



class Link:
    vk_id:int
    tg_id:int
    last_post:int
    user_id:int
    def __init__(self, vkid:int, tgid:int, userid:int, postid:int=None) -> None:
        self.vk_id = vkid
        self.tg_id = tgid
        self.post_id = postid
        self.user_id = userid

class User:
    user_id:int
    paid: bool

    def __init__(self, user_id:int, paid:bool) -> None:
        self.user_id = user_id
        self.paid = paid

    @property
    def max_links(self):
        return 5 if self.paid else 1
    
    @property
    def check_rate(self):
        #returns the time period (in seconds) between the checks of the user's link posts
        return 10*60 if self.paid else 60*60


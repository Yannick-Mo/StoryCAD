PREDEFINED = [
    {
        "title": "倒计时婚礼",
        "description": "婚礼当天，主角收到匿名信：\"你身边的人不是你以为的那个人。\" 距离仪式开始还有一小时。",
        "constraints": ["全程发生在婚礼场地内", "不能用手机", "必须有至少一次闪回"],
        "difficulty": "medium",
        "genre": "悬疑"
    },
    {
        "title": "反向穿越",
        "description": "一个现代程序员意外穿越到武侠世界，但他不是去当主角——他是去修BUG的。武林秘籍全部变成了乱码。",
        "constraints": ["不能有战斗场面", "必须使用计算机术语", "不能出现真实武功招式"],
        "difficulty": "hard",
        "genre": "网络爽文"
    },
    {
        "title": "零台词约会",
        "description": "两个哑巴在相亲。全程不能说一句话，全靠纸条、眼神和肢体语言。",
        "constraints": ["全篇无对话", "字数不超过2000字", "必须有甜蜜结局"],
        "difficulty": "hard",
        "genre": "言情"
    },
    {
        "title": "最后一碗面",
        "description": "城中村拆迁前夜，老面馆的最后一夜。熟客们陆续来吃最后一碗面。",
        "constraints": ["只能写一个场景", "必须有三个客人出场", "老板不能说话"],
        "difficulty": "easy",
        "genre": "现实主义"
    },
    {
        "title": "魔法失效之日",
        "description": "某天醒来，全世界的魔法突然消失了。魔法学院的学生们发现自己学的东西全部变成了废纸。",
        "constraints": ["没有反派", "必须有一个关键角色选择留下", "不能使用任何奇幻元素作为解决方案"],
        "difficulty": "medium",
        "genre": "奇幻"
    },
    {
        "title": "地铁上的陌生人",
        "description": "早高峰地铁上，主角发现对面坐着的陌生人正在哭泣。没人注意到他。",
        "constraints": ["只能用第三人称有限视角", "不能写内心独白", "地铁不能到站"],
        "difficulty": "medium",
        "genre": "现实主义"
    },
    {
        "title": "我是NPC",
        "description": "主角是网络小说里的路人甲，突然发现自己有了自我意识。但他不能OOC（脱离角色）。",
        "constraints": ["主角不能改变剧情主线", "可以尝试在夹缝中做小改变", "必须保持喜剧基调"],
        "difficulty": "hard",
        "genre": "网络爽文"
    },
    {
        "title": "一封没有寄出的信",
        "description": "整理遗物时发现一封写于五十年前的信，收件人还在世，但信从未寄出。",
        "constraints": ["现在和过去双线叙事", "信的内容不能直接写出", "必须有天气描写呼应情感"],
        "difficulty": "medium",
        "genre": "言情"
    },
    {
        "title": "深夜便利店",
        "description": "凌晨三点，便利店来了一个浑身湿透的小孩，说要买一包烟。",
        "constraints": ["只有一个店员和一个顾客", "不能解释小孩为什么湿透", "结局必须暧昧"],
        "difficulty": "easy",
        "genre": "悬疑"
    },
    {
        "title": "龙与外卖",
        "description": "一头龙用手机点了外卖。外卖小哥送到后发现收货地址是山顶的洞穴。",
        "constraints": ["龙不能变成人形", "外卖小哥不能害怕", "必须有差评"],
        "difficulty": "easy",
        "genre": "奇幻"
    },
    {
        "title": "一日重生",
        "description": "主角死后获得一次重生机会，但只能回到一天前的早晨。他必须在24小时内改变自己的死亡。",
        "constraints": ["不能重置时间（没有第二次重生）", "每次失败都会失去一部分记忆", "必须自然死亡才触发重生"],
        "difficulty": "hard",
        "genre": "悬疑"
    },
    {
        "title": "分手合约",
        "description": "为了合租押金不退，分手后的两人必须继续同居30天。他们签了一份合约。",
        "constraints": ["不能出现肢体接触", "台词可以用\"合同条款第X条\"开头", "必须有做饭场景"],
        "difficulty": "medium",
        "genre": "言情"
    },
    {
        "title": "修仙界公务员",
        "description": "主角穿越到修仙界，发现自己被分配到了仙界政务服务中心。每天处理各种奇葩业务。",
        "constraints": ["全程在政务大厅", "必须有排队叫号系统", "不能用武力解决问题", "必须有年度KPI考核"],
        "difficulty": "hard",
        "genre": "网络爽文"
    },
    {
        "title": "最后一个灯笼",
        "description": "古镇最后一个灯笼匠人，接到了一笔来自博物馆的订单——复制一百年前遗失的那盏镇街之宝。",
        "constraints": ["只能写三天时间", "必须有师徒对话", "不能直接描写灯笼成品"],
        "difficulty": "easy",
        "genre": "现实主义"
    },
    {
        "title": "会说话的猫",
        "description": "主角捡到一只会说话的猫。猫说：\"你三个月后会死。\" 然后就不肯再开口了。",
        "constraints": ["猫不能再次说话", "不能是梦", "结尾必须有反转"],
        "difficulty": "medium",
        "genre": "奇幻"
    },
]


def get_challenges(difficulty: str | None = None, genre: str | None = None) -> list[dict]:
    result = PREDEFINED[:]
    if difficulty:
        result = [c for c in result if c["difficulty"] == difficulty]
    if genre:
        result = [c for c in result if c["genre"] == genre]
    return result


def get_random_challenge() -> dict:
    import random
    return random.choice(PREDEFINED)

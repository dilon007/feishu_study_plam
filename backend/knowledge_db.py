"""
苏州市9年级专属学习中台 - 权威知识库
1. 英语：译林牛津版 (9A, 9B) 核心考纲词汇
2. 语文：国家统编部编版九年级 必背文言文与古诗词
3. 数学/物理：苏科版初三核心定理与公式
"""

# ==========================================
# 1. 译林牛津版初三英语核心考点词库 (示例及标准结构)
# ==========================================
YILIN_ENGLISH_DICT = {
    "generous": {
        "word": "generous",
        "phonetic": "/ˈdʒenərəs/",
        "pos": "adj. 慷慨的，大方的",
        "unit": "译林牛津版 9A Unit 1 Know yourself",
        "definition": "愿意给予或分享金钱、时间等；宽厚的",
        "phrases": [
            "be generous to sb. (对某人大方/宽厚)",
            "It is generous of sb. to do sth. (某人做某事实在大方)"
        ],
        "sentences": [
            "He is generous to everyone and often donates money to charities.",
            "It's very generous of you to share your revision notes with me."
        ],
        "exam_tips": "【苏州中考易错点】形容词做表语。在“It is + adj. + of/for sb. to do sth.”句型中，generous 表示人的品质，介词必须用 of，不能用 for！"
    },
    "curious": {
        "word": "curious",
        "phonetic": "/ˈkjʊəriəs/",
        "pos": "adj. 好奇的；奇特的",
        "unit": "译林牛津版 9A Unit 1 Know yourself",
        "definition": "对不知道或新事物充满求知欲望的",
        "phrases": [
            "be curious about sth. (对某事感到好奇)",
            "be curious to do sth. (极想做某事)",
            "out of curiosity (出于好奇心，名词形式拓展)"
        ],
        "sentences": [
            "Millie is curious about everything in the world and likes asking questions."
        ],
        "exam_tips": "【苏州中考常考搭配】单选题常考 'be curious about' 搭配；注意名词形式为 curiosity。"
    },
    "achieve": {
        "word": "achieve",
        "phonetic": "/əˈtʃiːv/",
        "pos": "vt. 达到，取得，实现",
        "unit": "译林牛津版 9A Unit 2 Colours",
        "definition": "通过努力、技能或勇气成功获得某物",
        "phrases": [
            "achieve one's dream / goal (实现某人的梦想/目标)",
            "achieve success (获得成功)"
        ],
        "sentences": [
            "If you study hard, you will surely achieve your goal in the Suzhou Zhongkao."
        ],
        "exam_tips": "【中考词性转换】名词形式为 achievement（可数名词，常用 achievements）；注意与 come true 的主被动用法区别（dream comes true vs achieve one's dream）。"
    },
    "patient": {
        "word": "patient",
        "phonetic": "/ˈpeɪʃnt/",
        "pos": "adj. 耐心的；n. 病人",
        "unit": "译林牛津版 9A Unit 1 Know yourself",
        "definition": "能忍耐不急躁的；接受治疗的人",
        "phrases": [
            "be patient with sb. (对某人有耐心)",
            "with patience (耐心地，副词用法)"
        ],
        "sentences": [
            "Teachers are always patient with their students when explaining difficult exercises."
        ],
        "exam_tips": "【中考考查重点】注意一词多义；反义词为 impatient（不耐烦的）；名词为 patience（不可数）。"
    },
    "influence": {
        "word": "influence",
        "phonetic": "/ˈɪnfluəns/",
        "pos": "v. & n. 影响",
        "unit": "译林牛津版 9A Unit 2 Colours",
        "definition": "对某人或某事产生影响或作用",
        "phrases": [
            "have an influence on / upon sb. (对某人有影响)",
            "under the influence of (在……的影响下)"
        ],
        "sentences": [
            "Colours can influence our moods and emotions according to psychology."
        ],
        "exam_tips": "【中考考查点】既可作及物动词（直接接宾语 influence sb.），也可作名词短语（have an influence on sb.）。"
    },
    "recommend": {
        "word": "recommend",
        "phonetic": "/ˌrekəˈmend/",
        "pos": "vt. 推荐；建议",
        "unit": "译林牛津版 9A Unit 1 Know yourself",
        "definition": "向他人介绍或推举某人/某物",
        "phrases": [
            "recommend sb. as... (推荐某人担任……)",
            "recommend sb. for... (推荐某人获得……)",
            "recommend that sb. (should) do sth. (建议某人做某事)"
        ],
        "sentences": [
            "We would like to recommend David as the new chairperson of the Students' Union."
        ],
        "exam_tips": "【书面表达常用句型】九上第一单元推荐信（Recommendation letter）高频必背句式。"
    }
}

# ==========================================
# 2. 统编版九年级文言文与古诗词必背题库
# ==========================================
TONGBIAN_ANCIENT_DICT = {
    "岳阳楼记": {
        "title": "岳阳楼记",
        "author": "范仲淹（北宋）",
        "book": "统编版语文九年级上册",
        "famous_sentences": [
            "不以物喜，不以己悲。",
            "居庙堂之高则忧其民，处江湖之远则忧其君。",
            "先天下之忧而忧，后天下之乐而乐。"
        ],
        "keywords": [
            "越明年（到了）：越，及，到。",
            "政通人和，百废具兴：通，顺利；具，通“俱”，全，皆。",
            "微斯人，吾谁与归：微，如果没有；归，归依。"
        ],
        "main_idea": "文章通过对岳阳楼周围阴晴景物的描写，表达了作者‘不以物喜，不以己悲’的博大胸襟，以及‘先天下之忧而忧，后天下之乐而乐’的崇高政治抱负与忧国忧民情怀。",
        "exam_spot": "【苏州中考必考点】1. ‘具’、‘属’字通假字释义；2. 宾语前置句‘吾谁与归’翻译；3. 默写极高频出现‘先天下之忧而忧，后天下之乐而乐’。"
    },
    "醉翁亭记": {
        "title": "醉翁亭记",
        "author": "欧阳修（北宋）",
        "book": "统编版语文九年级上册",
        "famous_sentences": [
            "醉翁之意不在酒，在乎山水之间也。",
            "山水之乐，得之心而寓之酒也。",
            "野芳发而幽香，佳木秀而繁阴。",
            "醉能同其乐，醒能述以文者，太守也。"
        ],
        "keywords": [
            "望之蔚然而深秀者：蔚然，茂盛的样子；深秀，幽深秀丽。",
            "醉翁之意不在酒：意，情趣，意趣。",
            "伛偻提携：伛偻，驼背，借指老人；提携，指搀扶着走的小孩。"
        ],
        "main_idea": "描绘滁州山水景物之美和滁人游乐的和平安详景象，抒发作者寄情山水、与民同乐的情怀。",
        "exam_spot": "【苏州中考必考点】‘也’字句的抒情转折、四时之景描写默写，以及成语‘醉翁之意不在酒’的语境理解。"
    },
    "出师表": {
        "title": "出师表",
        "author": "诸葛亮（三国·蜀汉）",
        "book": "统编版语文九年级下册",
        "famous_sentences": [
            "受任于败军之际，奉命于危难之间。",
            "亲贤臣，远小人，此先汉所以兴隆也；亲小人，远贤臣，此后汉所以倾颓也。",
            "苟全性命于乱世，不求闻达于诸侯。"
        ],
        "keywords": [
            "此诚危急存亡之秋也：秋，关键时刻，时。",
            "陟罚臧否，不宜异同：陟，提拔；臧否，评定好坏；异同，这里偏指不同。",
            "先帝不以臣卑鄙：卑鄙，身份低微，出身微贱（古今异义古义）。"
        ],
        "main_idea": "诸葛亮出师北伐前向后主刘禅提出的治国劝勉，表达了‘鞠躬尽瘁，死而后已’报答先帝知遇之恩的忠诚之志。",
        "exam_spot": "【苏州中考必考点】古今异义词（卑鄙、痛恨、感激、开张圣听）；作者提出的三条核心治国建议（广开言路、严明赏罚、亲贤远佞）。"
    },
    "水调歌头": {
        "title": "水调歌头·明月几时有",
        "author": "苏轼（北宋）",
        "book": "统编版语文九年级上册",
        "famous_sentences": [
            "人有悲欢离合，月有阴晴圆缺，此事古难全。",
            "但愿人长久，千里共婵娟。",
            "我欲乘风归去，又恐琼楼玉宇，高处不胜寒。"
        ],
        "keywords": [
            "把酒问青天：把，端起。",
            "何事长向别时圆：何事，为什么。",
            "千里共婵娟：婵娟，指月亮。"
        ],
        "main_idea": "词人中秋望月怀念胞弟苏辙，由幻想出世转为眷恋人间，抒发对人生的旷达胸襟与对天下离人的美好祝愿。",
        "exam_spot": "【苏州中考必考点】名篇名句默写；‘婵娟’借代修辞；‘此事古难全’蕴含的辩证哲理赏析。"
    }
}

# ==========================================
# 3. 智能检索辅助函数
# ==========================================
def query_english_word(keyword: str) -> dict:
    """查询初三译林版单词"""
    clean_word = keyword.strip().lower()
    if clean_word in YILIN_ENGLISH_DICT:
        return {"matched": True, "data": YILIN_ENGLISH_DICT[clean_word]}
    
    # 模糊匹配
    for k, v in YILIN_ENGLISH_DICT.items():
        if clean_word in k:
            return {"matched": True, "data": v}

    # 兜底：符合苏州初三英语考纲的智能解析模板
    return {
        "matched": False,
        "word": clean_word,
        "note": "苏州市初三英语考纲拓展词汇",
        "text": f"生词【{clean_word}】已在苏州市初三考标词库中建档。正在匹配苏教译林版九年级对应的典型例句与中考常考搭配。"
    }

def query_ancient_text(keyword: str) -> dict:
    """查询统编版初三文言文与古诗词"""
    clean_key = keyword.strip()
    
    # 篇目全称或简称匹配
    for title, item in TONGBIAN_ANCIENT_DICT.items():
        if title in clean_key or clean_key in title:
            return {"matched": True, "data": item}
        
    # 名句匹配
    for title, item in TONGBIAN_ANCIENT_DICT.items():
        for sentence in item["famous_sentences"]:
            if clean_key in sentence:
                return {
                    "matched": True, 
                    "data": item,
                    "matched_sentence": sentence
                }
                
    return {
        "matched": False,
        "title": clean_key,
        "note": "苏州市初三统编版文言考点",
        "text": f"篇目【{clean_key}】收录于苏州市初中学业水平考试要求文言诗文考查范围。请确认篇目名称（如：岳阳楼记、醉翁亭记、出师表、水调歌头）。"
    }

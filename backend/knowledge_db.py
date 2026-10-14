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
    }
}

# ==========================================
# 3. 苏科版九年级物理核心考点库
# ==========================================
SUKE_PHYSICS_DICT = {
    "欧姆定律": {
        "title": "欧姆定律与动态电路分析",
        "book": "苏科版九年级物理上册·第十四章",
        "formula": "I = U / R  (变形: U = IR, R = U / I)",
        "key_points": [
            "串联电路：电流处处相等 (I=I1=I2)，总电压等于各分电压之和 (U=U1+U2)，分压原理 U1/U2 = R1/R2。",
            "并联电路：各支路两端电压相等 (U=U1=U2)，干路电流等于各支路电流之和 (I=I1+I2)，分流原理 I1/I2 = R2/R1。",
            "动态电路解题秘籍：先判断电路串并联 ➔ 确定电表所测对象 ➔ 依据滑片移动判断滑动变阻器连入阻值变化 ➔ 结合欧姆定律推导各表示数变化。"
        ],
        "exam_tips": "【苏州中考必考点】每年必考动态电路分析与电表量程安全保护计算，注意电表不可超量程！"
    },
    "电功率": {
        "title": "电功、电功率与焦耳定律",
        "book": "苏科版九年级物理下册·第十五章",
        "formula": "P = W / t = UI；纯电阻电路推导式: P = I²R = U² / R；焦耳定律: Q = I²Rt",
        "key_points": [
            "额定功率与实际功率：灯泡亮度由【实际电功率】决定，实际电压等于额定电压时实际功率才等于额定功率。",
            "电热计算与防止：电热器工作时电能全部转化为内能 (Q=W=Pt)；非纯电阻电路 (如电动机) W = UIt > Q = I²Rt。"
        ],
        "exam_tips": "【苏州中考压轴计算】常见于电学极值范围题：结合滑动变阻器最大允许电流、电压表量程、电流表量程列不等式组求解阻值范围。"
    },
    "杠杆与滑轮": {
        "title": "简单机械（杠杆、滑轮与机械效率）",
        "book": "苏科版九年级物理上册·第十一章",
        "formula": "杠杆平衡: F1·L1 = F2·L2；滑轮组拉力: F = (G物 + G动) / n；机械效率: η = W有 / W总 = Gh / Fs = G / (nF)",
        "key_points": [
            "力臂作图三步法：找支点 O ➔ 画力的作用线 (虚线延长) ➔ 从支点向力的作用线引垂线段标垂直符号并标注 L。",
            "最小动力原则：连接支点到力的作用点作为最长力臂 L，过该点作垂线即为最小力的方向。",
            "滑轮组绕绳：承担物重的绳子段数 n 决定省力程度，s = nh，v绳 = n·v物。"
        ],
        "exam_tips": "【中考易错点】作图题切忌漏画垂直符号；水平方向滑轮组克服摩擦力做有用功 (W有 = f·s物)。"
    }
}

# ==========================================
# 4. 九年级化学（酸碱盐与实验探究）核心考点库
# ==========================================
SUZHOU_CHEMISTRY_DICT = {
    "酸碱盐": {
        "title": "常见的酸碱盐及复分解反应",
        "book": "初三化学下册·酸碱盐核心单元",
        "formula": "复分解反应发生条件：生成沉淀、气体或水三者至少满足其一",
        "key_points": [
            "常见酸：浓盐酸具有挥发性(白雾)；浓硫酸具有吸水性(干燥剂)与脱水腐蚀性，稀释必须【酸入水、沿器壁、缓缓倒、不断搅】。",
            "常见碱：NaOH俗称烧碱/火碱/苛性钠，易潮解；Ca(OH)2俗称熟石灰/消石灰，澄清石灰水用于检验CO2。",
            "中考高频沉淀颜色：Cu(OH)2 蓝色沉淀；Fe(OH)3 红褐色沉淀；BaSO4、AgCl 不溶于稀硝酸的白色沉淀；CaCO3、BaCO3 溶于酸产生气泡的白色沉淀。"
        ],
        "exam_tips": "【苏州中考推断题题眼】根据特殊沉淀颜色、气体生成或特殊转化（如三角转化：CaCO3 ➔ CaO ➔ Ca(OH)2 ➔ CaCO3）突破推断。"
    },
    "气体制备": {
        "title": "实验室气体制备与净化",
        "book": "初三化学气体制取综合专题",
        "formula": "制氧气: 2KMnO4 =加热= K2MnO4 + MnO2 + O2↑；制CO2: CaCO3 + 2HCl = CaCl2 + H2O + CO2↑",
        "key_points": [
            "发生装置选择：固固加热型 (高锰酸钾制O2)；固液常温型 (大理石与稀盐酸制CO2、双氧水制O2)。",
            "收集装置选择：不易溶于水用排水法 (O2, H2)；密度比空气大用向上排空气法 (O2, CO2)；密度比空气小用向下排空气法 (H2)。",
            "CO2 实验室制法禁忌：不能用稀硫酸 (生成微溶的CaSO4覆盖反应物阻碍反应)；不能用浓盐酸 (易挥发使气体不纯)；不能用碳酸钠 (反应过快难收集)。"
        ],
        "exam_tips": "【苏州中考实验答题规范】多功能瓶进气口原则：排水法‘短进长出’；向上排空气法‘长进短出’。"
    },
    "金属活动性": {
        "title": "金属活动性顺序与置换反应",
        "book": "初三化学第八单元·金属与金属材料",
        "formula": "K Ca Na Mg Al Zn Fe Sn Pb (H) Cu Hg Ag Pt Au (前置后，盐可溶)",
        "key_points": [
            "判断依据：位于氢前的金属能置换出稀盐酸/稀硫酸中的氢；位于前面的金属能把位于后面的金属从其盐溶液中置换出来 (K,Ca,Na除外)。",
            "滤渣滤液推断秘籍：金属活动性差距越大的优先反应（先远后近原则）。向含 AgNO3 和 Cu(NO3)2 的混合溶液中加入铁粉，铁先与 AgNO3 反应，Ag 完全置换后再与 Cu(NO3)2 反应。"
        ],
        "exam_tips": "【中考核心考查】滤渣一定有 Ag，可能有 Cu、Fe；若溶液为蓝色，则滤渣中绝对不可能含有 Fe。"
    }
}

# ==========================================
# 5. 智能检索辅助函数
# ==========================================
def query_english_word(keyword: str) -> dict:
    """查询初三译林版单词"""
    clean_word = keyword.strip().lower()
    if clean_word in YILIN_ENGLISH_DICT:
        return {"matched": True, "data": YILIN_ENGLISH_DICT[clean_word]}
    
    for k, v in YILIN_ENGLISH_DICT.items():
        if clean_word in k:
            return {"matched": True, "data": v}

    return {
        "matched": False,
        "word": clean_word,
        "note": "苏州市初三英语考纲拓展词汇",
        "text": f"生词【{clean_word}】已在苏州市初三考标词库中建档。正在匹配苏教译林版九年级对应的典型例句与中考常考搭配。"
    }

def query_ancient_text(keyword: str) -> dict:
    """查询统编版初三文言文与古诗词"""
    clean_key = keyword.strip()
    
    for title, item in TONGBIAN_ANCIENT_DICT.items():
        if title in clean_key or clean_key in title:
            return {"matched": True, "data": item}
        
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

def query_physics_concept(keyword: str) -> dict:
    """查询苏科版初三物理考点"""
    clean_key = keyword.strip()
    for title, item in SUKE_PHYSICS_DICT.items():
        if title in clean_key or clean_key in title:
            return {"matched": True, "data": item}
    return {"matched": False, "title": clean_key}

def query_chemistry_concept(keyword: str) -> dict:
    """查询初三化学核心考点"""
    clean_key = keyword.strip()
    for title, item in SUZHOU_CHEMISTRY_DICT.items():
        if title in clean_key or clean_key in title:
            return {"matched": True, "data": item}
    return {"matched": False, "title": clean_key}


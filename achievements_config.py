# achievements_config.py

ACHIEVEMENTS = {
    # ── 通常実績・追加実績 ──
    "not_admin": {"name": "あなたは管理者じゃないでしょ？", "description": "鯖内で表示される名前を「ぴくせる」にして「ストゼロ」を含むメッセージを発言する。", "is_hidden": False},
    "buy_anger": {"name": "怒りを買うよ？", "description": "「ぽこでん」と発言する。", "is_hidden": False},
    "private_life_manager": {"name": "私生活管理者", "description": "「ピコハン」と「ぴくせる」を含む発言をする。", "is_hidden": False},
    "minecraft_pro": {"name": "マインクラフトプロ？", "description": "「シルクタッチ強化」と発言する。", "is_hidden": False},
    "staple_is_mic": {"name": "主食はマイク", "description": "累計VC接続時間24時間に達する。", "is_hidden": False},
    "trash_talk": {"name": "ぽい捨てするなよ？", "description": "@ばうむ＋画像の添付の発言する。", "is_hidden": False},
    "noisy": {"name": "うるさい", "description": "#が文頭に入っていて15字以上のメッセージの発言をする。", "is_hidden": False},
    "sake_addict": {"name": "酒カス", "description": "最初の発言から3分以内に酒に関する発言を5個する。", "is_hidden": False},
    "energy_addict": {"name": "エナカス", "description": "最初の発言から3分以内にエンドリに関する発言を5個する。", "is_hidden": False},
    "no_alcohol_ii": {"name": "アルハラすんなよ！！！", "description": "22時以降に酒関連の発言をする。", "is_hidden": False},
    "genki": {"name": "げんき！！！！", "description": "「わんだほい」と発言する。", "is_hidden": False},
    "cold_laugh": {"name": "...w", "description": "冷笑する。", "is_hidden": False},
    "moyashi": {"name": "もやし", "description": "文章中に1を含めた発言をする。", "is_hidden": False},
    "hage": {"name": "はげちゃうわ", "description": "「はげ」を含める発言する。", "is_hidden": False},
    "stalker": {"name": "ストーカー", "description": "同じ人返信又はリアクションを24時間以内に合計10回する。", "is_hidden": False},
    "not_twilight": {"name": "ここは黄昏ではありません", "description": "暴走ch以外でえらこ掘りたいと発言する。", "is_hidden": False},
    "typing_no_need": {"name": "文字起こし不要？", "description": "24時間以内に100メッセージ送信する。", "is_hidden": False},
    "spam_king": {"name": "連投王", "description": "連続で5通のメッセージを送信する。", "is_hidden": False},
    "midnight_talker": {"name": "深夜の語り部", "description": "深夜0時以降〜朝4時にVCへ参加する。", "is_hidden": False},
    "empathy_storm": {"name": "共感の嵐", "description": "他のメンバーのメッセージにリアクション50回をつける。", "is_hidden": False},
    "emoji_artisan": {"name": "絵文字職人", "description": "サーバーのカスタム絵文字を累計100使う。", "is_hidden": False},
    "bot_best_friend": {"name": "botの親友", "description": "botに対してコマンドを20回実行する。", "is_hidden": False},
    "night_owl": {"name": "夜更かしの民", "description": "深夜2時～朝4時の間にメッセージを送信する。", "is_hidden": False},
    "silent_supporter": {"name": "サイレントサポーター", "description": "ミュートのまま1時間VCに接続する。", "is_hidden": False},
    "typo": {"name": "誤字ですよ", "description": "1分以内に2回自分のメッセージを編集する。", "is_hidden": False},
    
    # 画像追加分の実績
    "among_us": {"name": "アモアスですか？", "description": "「人狼」と言う", "is_hidden": False},
    "sound_gamer": {"name": "貴様ッ…音ゲーマーだなっ！！", "description": "「ゴママヨ」と言う", "is_hidden": False},
    "mention_fail": {"name": "メンション失敗（笑）", "description": "「@ユーザー名」というメンションになっていないものを送信する", "is_hidden": False},
    "wrong_channel": {"name": "淫夢チャンネルはここではないですよ！早く気づいて！", "description": "「やりますねぇ」と暴走機関車聞き専以外で言う", "is_hidden": False},
    "playback_fail": {"name": "再生できてませんよ", "description": "VCに入っていない状態で「m!p https://」と言う", "is_hidden": False},
    "nothing_tale": {"name": "無から始まる物語", "description": "U+200bを単体で打つ", "is_hidden": False},
    "you_free": {"name": "あなた暇なの？", "description": "VCに24時間入る", "is_hidden": False},
    
    # チャンネル指定系
    "zatsudan_1": {"name": "れっつづだん！", "description": "ざつだん1で発言する", "is_hidden": False},
    "vomit": {"name": "辛いことは全部吐き出して", "description": "愚痴・発狂で発言する", "is_hidden": False},
    "twitter_faction": {"name": "Twitter派だよね？", "description": "X宣伝で発言する", "is_hidden": False},
    
    "shining": {"name": "光ってる？", "description": "「ぴくせる」と言う", "is_hidden": False},
    "bad_words": {"name": "悪口はダメですよ？", "description": "「バカ」「クソ」「カス」のどれかを言う（かな・漢字・ローマ字対応）", "is_hidden": False},
    "shiritori": {"name": "り……隣人！", "description": "「しりとり」と言う", "is_hidden": False},
    "dice_madness": {"name": "そんなダイス使わんやろ", "description": "100d100000と打つ", "is_hidden": False},

    # ── 隠し実績 ──
    "black_history": {"name": "黒歴史", "description": "1分以内に3回自分の発言したメッセージを消す。", "is_hidden": True},
    "you_lose": {"name": "負けました", "description": "隠し実績を含む全ての実績を解除する。", "is_hidden": True},
    "all_unlock_q": {"name": "全実績解除？", "description": "隠し実績以外の実績を全部解除する。", "is_hidden": True},
}
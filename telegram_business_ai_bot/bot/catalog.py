from typing import TypedDict


class Product(TypedDict):
    name: str
    description: str
    price: str
    weight: str
    origin: str
    photo: str
    photo_url: str


Catalog = dict[str, dict[str, list[Product]]]
ProductRef = tuple[str, str, int]


CATALOG: Catalog = {
    'Сухофрукты': {
        'Курага': [
            {
                'name': 'Абрикос сушёный (урюк) отборный, Таджикистан 1кг',
                'description': 'Сушёные абрикосы (урюк) с косточкой, премиум качество. Отборный урюк сладкий, вкусный.',
                'price': '690 руб.',
                'weight': '1 кг',
                'origin': 'Таджикистан',
                'photo': 'assets/products/suhofrukty/kuraga/01_kuraga_naturalnaya_tureckaya_dzhambo_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Курага жёлтая, отборная, Таджикистан, 1кг',
                'description': 'Курага отборная, сладкая, чистая из Таджикистана. Крупные плода абрикоса. Сорт: "Бобои"',
                'price': '720 руб.',
                'weight': '1 кг',
                'origin': 'Таджикистан',
                'photo': 'assets/products/suhofrukty/kuraga/02_kuraga_zheltaya_kislo_sladkaya_otbornaya_tadzhikistan_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Курага красная, отборная, Таджикистан, 1кг',
                'description': 'Курага отборная, сладкая, чистая из Таджикистана. Крупные плода абрикоса',
                'price': '750 руб.',
                'weight': '1 кг',
                'origin': 'Таджикистан',
                'photo': 'assets/products/suhofrukty/kuraga/03_kuraga_saharnaya_otbornaya_tadzhikistan_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Курага натуральная турецкая джамбо, 1кг',
                'description': 'Натуральная турецкая курага из Турции, шоколадная курага. Высший сорт, вкусный и полезный.',
                'price': '780 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/suhofrukty/kuraga/04_kuraga_krasnaya_otbornaya_tadzhikistan_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Ядра абрикосовых косточек, Таджикистан, 500г',
                'description': 'Качественный продукт от МирСухофруктов для ежедневного рациона и подарков.',
                'price': '810 руб.',
                'weight': '500 г',
                'origin': 'Таджикистан',
                'photo': 'assets/products/suhofrukty/kuraga/05_kuraga_zheltaya_otbornaya_tadzhikistan_1kg.jpg',
                'photo_url': '',
            },
        ],
        'Изюм': [
            {
                'name': 'Изюм кисло-сладкий крупный джамбо, Чили 500г',
                'description': 'Изюм без косточек, кисло-сладкий из Чили, крупный, отборный',
                'price': '430 руб.',
                'weight': '500 г',
                'origin': 'Чили',
                'photo': 'assets/products/suhofrukty/izyum/01_izyum_kishmish_krupnyy_sladkiy_uzbekistan_500g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Изюм жёлтый кисло-сладкий, Узбекистан 500г',
                'description': 'Изюм без косточек, кисло-сладкий из Узбекистана',
                'price': '460 руб.',
                'weight': '500 г',
                'origin': 'Узбекистан',
                'photo': 'assets/products/suhofrukty/izyum/02_izyum_maloyar_korichnevyy_iran_500g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Изюм Малояр коричневый, Иран 500г',
                'description': 'Изюм малаяр – виноград светлых сортов, бережно высушенный на солнце. По полезности почти не уступает свежему винограду, так как сохраняет в себе витамины.',
                'price': '490 руб.',
                'weight': '500 г',
                'origin': 'Иран',
                'photo': 'assets/products/suhofrukty/izyum/03_izyum_krasnyy_terma_kislo_sladkiy_uzbekistan_500g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Изюм кишмиш крупный сладкий, Узбекистан 500г',
                'description': 'Изюм без косточек, крупный гибрид, гигант, сладкий из Узбекистана, подсушёный в тени.',
                'price': '520 руб.',
                'weight': '500 г',
                'origin': 'Узбекистан',
                'photo': 'assets/products/suhofrukty/izyum/04_orehovaya_smes_s_izyumom_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Изюм с хвостиком сладкий, Узбекистан 500г',
                'description': 'Изюм (кишмиш) без косточек, сладкий из Узбекистана, подсушёный в тени.',
                'price': '550 руб.',
                'weight': '500 г',
                'origin': 'Узбекистан',
                'photo': 'assets/products/suhofrukty/izyum/01_izyum_kishmish_krupnyy_sladkiy_uzbekistan_500g.jpg',
                'photo_url': '',
            },
        ],
        'Финики': [
            {
                'name': 'Финики сушёные арабские, 1кг',
                'description': 'Финики сушёные с косточкой, иранские, сладкие. Среднего размера. Сорт: Арабские',
                'price': '520 руб.',
                'weight': '1 кг',
                'origin': 'Иран',
                'photo': 'assets/products/suhofrukty/finiki/01_finiki_sushenye_tunisskie_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Финики сушёные тунисские, 1кг',
                'description': 'Финики с косточкой Алжирские/Тунисские, сладкие.',
                'price': '550 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/suhofrukty/finiki/02_naturalnye_finiki_sushenye_tunisskie_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Финики сушёные иранские "Соир / Алмаз", 1кг',
                'description': 'Финики сушёные с косточкой, иранские, сладкие. Среднего размера. Сорт: иранские. Алмаз, Соир',
                'price': '580 руб.',
                'weight': '1 кг',
                'origin': 'Иран',
                'photo': 'assets/products/suhofrukty/finiki/03_finiki_sushenye_zohidi_bez_sahara_iran_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Натуральные финики сушёные тунисские, 500г',
                'description': 'Натуральные финики, без сахара, с косточкой Алжирские/Тунисские, сладкие.',
                'price': '610 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/suhofrukty/finiki/04_finiki_sushenye_arabskie_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Натуральные финики сушёные тунисские, 1кг',
                'description': 'Натуральные финики, без сахара, с косточкой Алжирские/Тунисские, сладкие.',
                'price': '640 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/suhofrukty/finiki/05_naturalnye_finiki_sushenye_tunisskie_500g.jpg',
                'photo_url': '',
            },
        ],
        'Цукаты': [
            {
                'name': 'Папайя жёлтые палочки, 1кг',
                'description': 'Дыня жёлтые палочки',
                'price': '460 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/suhofrukty/finiki/01_finiki_sushenye_tunisskie_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Цукаты из ананаса кубики, 1кг',
                'description': 'Цукаты кубики из папайи и/или ананаса, кисло-сладкие.',
                'price': '490 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/suhofrukty/finiki/02_naturalnye_finiki_sushenye_tunisskie_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Ананас сушёный натуральный, 500г',
                'description': 'Ананасовые кольца вяленые, вкусные, полезные и натуральные.',
                'price': '520 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/suhofrukty/finiki/03_finiki_sushenye_zohidi_bez_sahara_iran_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Кумкват оранжевый, цукаты, 1кг',
                'description': 'Качественный продукт от МирСухофруктов для ежедневного рациона и подарков.',
                'price': '550 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/suhofrukty/finiki/04_finiki_sushenye_arabskie_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Манго ломтики жёлтый цукаты, 1кг',
                'description': 'Манго осмотически обезвоженное с сахаром, цукаты.',
                'price': '580 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/suhofrukty/finiki/05_naturalnye_finiki_sushenye_tunisskie_500g.jpg',
                'photo_url': '',
            },
        ],
        'Прочие сухофрукты': [
            {
                'name': 'Райские яблоки сушёные, 500г',
                'description': 'Райские яблочки из Китая, с сахаром',
                'price': '390 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/suhofrukty/prochie_suhofrukty/01_grusha_sushenaya_dolki_dlya_kompota_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Инжир сушёный натуральный, 500г',
                'description': 'Натуральный турецкий инжир без сахара, вкусный.',
                'price': '420 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/suhofrukty/prochie_suhofrukty/02_kumkvat_krasnyy_cukaty_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Слива чёрная сушёная натуральная половинки, Армения 500г',
                'description': 'Натуральная сушёная слива— высокое качество, с кисло-сладким вкусом.',
                'price': '450 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/suhofrukty/prochie_suhofrukty/03_inzhir_sushenyy_naturalnyy_500g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Яблоко сушёное для компота ломтики, 1кг',
                'description': 'Сушёное яблоко для компота.',
                'price': '480 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/suhofrukty/prochie_suhofrukty/04_kokosovye_lomtiki_sushenye_500g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Груша сушёная дольки для компота, 1кг',
                'description': 'Груша резанные дольки натуральные для компота.',
                'price': '510 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/suhofrukty/prochie_suhofrukty/01_grusha_sushenaya_dolki_dlya_kompota_1kg.jpg',
                'photo_url': '',
            },
        ],
    },
    'Орехи': {
        'Фисташки': [
            {
                'name': 'Фисташки турецкие жареные солёные, 500г',
                'description': 'Отборные горные турецкие фисташки, высший сорт, слабосолёные. (Чанкая, Cankaya)',
                'price': '1190 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/fistashki/01_fistashki_zharenye_solenye_iranskie_sort_ahmadi_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Ядра фисташек очищенные крупные, 1кг',
                'description': 'Вкусные, полезные и отборные ядра фисташек без соли.',
                'price': '1220 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/fistashki/02_fistashki_tureckie_zharenye_solenye_500g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Фисташки сырые крупные американские, 1кг',
                'description': 'Фисташки крупные, не жареные и не солёные. Страна произростания — США. Отборный сорт',
                'price': '1250 руб.',
                'weight': '1 кг',
                'origin': 'США',
                'photo': 'assets/products/orehi/fistashki/03_yadra_fistashek_ochischennye_krupnye_250g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Фисташки солёные, Иранские "Фандоги", 1кг',
                'description': 'Фисташки жареные, солёные, Иранские. Сорт — Фандоги, отборные.',
                'price': '1280 руб.',
                'weight': '1 кг',
                'origin': 'Иран',
                'photo': 'assets/products/orehi/fistashki/04_yadra_fistashek_ochischennye_krupnye_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Фисташки жареные солёные, Иранские, сорт Ахмади, 1кг',
                'description': 'Фисташки Иранские, жареные солёные, сорт — Ахмади, отборные, длинный калибр.',
                'price': '1310 руб.',
                'weight': '1 кг',
                'origin': 'Иран',
                'photo': 'assets/products/orehi/fistashki/05_fistashki_solenye_iranskie_fandogi_1kg.jpg',
                'photo_url': '',
            },
        ],
        'Миндаль и фундук': [
            {
                'name': 'Миндаль сырой отборный, 1кг',
                'description': 'Вкусный очищенный от скорлупы калифорнийский сырой миндаль.',
                'price': '780 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/mindal_i_funduk/01_mindal_syroy_krupnyy_chili_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Фундук в белом шоколаде, 1кг',
                'description': 'Вкусный, отборный, жареный фундук в белой глазури',
                'price': '810 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/mindal_i_funduk/02_mindal_zharenyy_otbornyy_500g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Фундук в тёмном шоколаде, 1кг',
                'description': 'Вкусный, отборный, жареный фундук в тёмной глазури',
                'price': '840 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/mindal_i_funduk/03_funduk_v_belom_shokolade_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Фундук сырой светлый, 500г',
                'description': 'Вкусный и полезный сырой фундук из Дагестан',
                'price': '870 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/mindal_i_funduk/04_mindalnye_lepestki_500g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Фундук сырой тёмный, 1кг',
                'description': 'Фундук из Абхазии, крупный 17+, свежий урожай',
                'price': '900 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/mindal_i_funduk/05_funduk_syroy_svetlyy_1kg.jpg',
                'photo_url': '',
            },
        ],
        'Грецкий орех': [
            {
                'name': 'Грецкий орех очищенный, отборный, 500г',
                'description': 'Качественный продукт от МирСухофруктов для ежедневного рациона и подарков.',
                'price': '780 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/greckiy_oreh/01_greckiy_oreh_v_skorlupe_chili_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Грецкий орех очищенный четвертинки, 500г',
                'description': 'Грецкий орех очищенный, "рядовка", вкусные.',
                'price': '810 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/greckiy_oreh/02_peregorodki_greckih_orehov_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Грецкий орех в скорлупе, Китай, 1кг',
                'description': 'Качественный продукт от МирСухофруктов для ежедневного рациона и подарков.',
                'price': '840 руб.',
                'weight': '1 кг',
                'origin': 'Китай',
                'photo': 'assets/products/orehi/greckiy_oreh/03_greckiy_oreh_ochischennyy_otbornyy_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Грецкий орех в скорлупе, Чили 1кг',
                'description': 'Отборный, крупный чилийский грецкий орех. Свежий урожай',
                'price': '870 руб.',
                'weight': '1 кг',
                'origin': 'Чили',
                'photo': 'assets/products/orehi/greckiy_oreh/04_greckiy_oreh_ochischennyy_babochka_chili_500g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Перегородки грецких орехов, 500г',
                'description': 'Перегородки грецкого ореха — чистые.',
                'price': '900 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/greckiy_oreh/05_greckiy_oreh_ochischennyy_otbornyy_500g.jpg',
                'photo_url': '',
            },
        ],
        'Ореховые смеси': [
            {
                'name': 'Арахис в скорлупе обжаренный, 500г',
                'description': 'Вкусный жареный арахис в скорлупе (неочищенный).',
                'price': '390 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/orehovye_smesi/01_arahis_zharenyy_uzbekistan_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Фруктово-ореховая смесь, 500г',
                'description': 'Вкусная и полезная смесь из сухофруктов и орехов.',
                'price': '920 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/orehovye_smesi/02_pekan_ochischennyy_syroy_argentina_500g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Бразильский орех Medium, 500г',
                'description': 'Очищенный разильский орех — среднего размера (Medium), страна эспортёр: Боливия.',
                'price': '450 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/orehovye_smesi/03_arahis_v_skorlupe_obzharennyy_500g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Арахис сырой красный, Узбекистан, 1кг',
                'description': 'Вкусный очищенный арахис из Узбекистана, урожай 2023года.',
                'price': '480 руб.',
                'weight': '1 кг',
                'origin': 'Узбекистан',
                'photo': 'assets/products/orehi/orehovye_smesi/04_brazilskiy_oreh_medium_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Пастила фруктовая натуральная, 5шт',
                'description': 'Пастила скрученная вкусная из разных фруктов. 5шт ассорти в комплекте.',
                'price': '510 руб.',
                'weight': '0.86 кг с упаковкой',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/orehovye_smesi/05_arahis_syroy_krasnyy_uzbekistan_500g.jpg',
                'photo_url': '',
            },
        ],
        'Орехи в глазури': [
            {
                'name': 'Кешью в тёмном шоколаде, 500г',
                'description': 'Вкусный, отборный, жареный кешью в тёмной глазури',
                'price': '920 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/orehi_v_glazuri/01_halva_uzbekskaya_shokoladno_molochnaya_zebra_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Халва узбекская шоколадно-молочная "Зебра", 1кг',
                'description': 'Вкусная узбекская халва.',
                'price': '490 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/orehi_v_glazuri/02_arahis_v_kunzhute_s_medom_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Арахис в разноцветном сахаре, 1кг',
                'description': 'Хрустящий арахис в цветном сахаре, в сахарной глазури.',
                'price': '520 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/orehi_v_glazuri/03_arahis_v_raznocvetnom_sahare_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Арахис жареный со вкусом креветок, 500г',
                'description': 'Арахис очищенный жареный со кусом креветок',
                'price': '480 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/orehi_v_glazuri/04_arahis_zharenyy_so_vkusom_barbekyu_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Шоколадные камушки драже, 500г',
                'description': 'Качественный продукт от МирСухофруктов для ежедневного рациона и подарков.',
                'price': '510 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/orehi/orehi_v_glazuri/05_halva_uzbekskaya_shokoladno_molochnaya_zebra_500g.jpg',
                'photo_url': '',
            },
        ],
    },
    'Бакалея': {
        'Семена': [
            {
                'name': 'Семечки тыквенные сырые неочищенные, 2кг',
                'description': 'Тыквенные семечки — неочищенные, сырые, собранные в Волгоградской области. Урожай осени 2024 года.',
                'price': '360 руб.',
                'weight': '2 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/bakaleya/semena/01_kunzhut_chernyy_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Гречка зелёная, 1кг',
                'description': 'Непропаренная зеленая гречка.',
                'price': '390 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/bakaleya/semena/02_chay_110_krupnolistovoy_zelenyy_chay_400g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Семена чиа, 1кг',
                'description': 'Семена чиа',
                'price': '420 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/bakaleya/semena/03_kunzhut_belyy_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Чай 95, крупнолистовой зелёный чай, 400г',
                'description': 'Зеленый чай "95" относится к превосходным крупнолистовым чаям с характерным для него терпким вкусом. Зеленый чай славится своей уникальной способностью утолять жажду и охлаждать организм, что весьма ценно в любой жаркой стране.\nКитайский зеленый чай ТОЗА № 95 сорт GUN POWDER, с восточным ароматом, отличающиеся крупными листьями (форма чая комковой), популярны еще с времен Советского Союза, сорта родом из Узбекистана и называются КОК-ЧОЙ',
                'price': '650 руб.',
                'weight': '400 г',
                'origin': 'Узбекистан',
                'photo': 'assets/products/bakaleya/semena/04_kumkvat_zelenyy_cukaty_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Семечки тыквенные сырые неочищенные, 1кг',
                'description': 'Тыквенные семечки — неочищенные, сырые, собранные в Волгоградской области. Урожай осени 2024 года.',
                'price': '480 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/bakaleya/semena/01_kunzhut_chernyy_1kg.jpg',
                'photo_url': '',
            },
        ],
        'Крупы и бобовые': [
            {
                'name': 'Булгур, крупа пшеничная, 1кг',
                'description': 'Булгур — лак, приготовленный из сушеной дробленой пшеницы преимущественно твердых сортов',
                'price': '330 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/bakaleya/krupy_i_bobovye/01_oves_neochischennyy_v_obolochke_2kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Нут горох 8+, Узбекистан, 1кг',
                'description': 'Горох - нут, калибр 8+, отборный из Узбекистана. Получится вкусная еда. Также подходит для проращивания',
                'price': '360 руб.',
                'weight': '1 кг',
                'origin': 'Узбекистан',
                'photo': 'assets/products/bakaleya/krupy_i_bobovye/02_barbaris_sushenyy_chernyy_iranskiy_50g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Рис Осман круглозёрный, 1кг',
                'description': 'Белый круглозерный, краснодарский — хорошо варится, не превращаться в кашу, на зернышках не имеет трещин и обломанных краев, содержит меньший процент крахмальности.  Рассыпчатый и нежный злак. Высший сорт. Также отлично подходит для плова.',
                'price': '390 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/bakaleya/krupy_i_bobovye/04_barbaris_sushenyy_chernyy_iranskiy_500g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Фасоль "Красная", 1кг',
                'description': 'Фасоль "Красная", с красным окрасом. Вкусная с высоким содержанием белков.',
                'price': '420 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/bakaleya/krupy_i_bobovye/05_fasol_seraya_2kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Булгур, крупа пшеничная, 500г',
                'description': 'Булгур — лак, приготовленный из сушеной дробленой пшеницы преимущественно твердых сортов',
                'price': '450 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/bakaleya/krupy_i_bobovye/01_oves_neochischennyy_v_obolochke_2kg.jpg',
                'photo_url': '',
            },
        ],
        'Специи': [
            {
                'name': 'Кукуруза для попкорна, 500г',
                'description': 'Кукуруза для попкорна - это специальный сорт кукурузы, предназначенный для приготовления попкорна.',
                'price': '240 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/bakaleya/specii/01_grusha_vyalenaya_armyanskaya_500g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Персик вяленый натуральный армянский, 500г',
                'description': 'Персик вяленый армянский - это изысканный деликатес, полученный из отборных сортов армянских персиков. Каждый плод тщательно подвергается процессу высушивания, при котором сохраняются все естественные вкусовые качества и питательные вещества.\n\nАрмянский вяленый персик обладает неповторимым сочным вкусом, сладостью и ароматом, которые сохраняются благодаря специальным методам обработки. Этот продукт является естественным источником витаминов, минералов и антиоксидантов, таких как витамин А и С, калий, магний и другие, способствующих поддержанию здоровья.\n\nПерсик вяленый армянский идеально подходит в качестве полезной и вкусной закуски к чаю или кофе, а также может использоваться в кулинарии для приготовления различных десертов, компотов, смузи и других блюд. Благодаря своей долгой стойкости и удобной форме, этот продукт отлично подходит для хранения и транспортировки, делая его прекрасным выбором как для домашнего использования, так и для подарков или добавления в подарочные корзины.',
                'price': '270 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/bakaleya/specii/02_keshyu_zharenyy_so_speciyami_500g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Кешью жареный со специями, 1кг',
                'description': 'Качественный продукт от МирСухофруктов для ежедневного рациона и подарков.',
                'price': '980 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/bakaleya/specii/03_persik_vyalenyy_naturalnyy_armyanskiy_500g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Персик вяленый натуральный армянский, 500г',
                'description': 'Персик вяленый армянский - это изысканный деликатес, полученный из отборных сортов армянских персиков. Каждый плод тщательно подвергается процессу высушивания, при котором сохраняются все естественные вкусовые качества и питательные вещества.\n\nАрмянский вяленый персик обладает неповторимым сочным вкусом, сладостью и ароматом, которые сохраняются благодаря специальным методам обработки. Этот продукт является естественным источником витаминов, минералов и антиоксидантов, таких как витамин А и С, калий, магний и другие, способствующих поддержанию здоровья.\n\nПерсик вяленый армянский идеально подходит в качестве полезной и вкусной закуски к чаю или кофе, а также может использоваться в кулинарии для приготовления различных десертов, компотов, смузи и других блюд. Благодаря своей долгой стойкости и удобной форме, этот продукт отлично подходит для хранения и транспортировки, делая его прекрасным выбором как для домашнего использования, так и для подарков или добавления в подарочные корзины.',
                'price': '330 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/bakaleya/specii/04_grusha_vyalenaya_armyanskaya_1kg.jpg',
                'photo_url': '',
            },
            {
                'name': 'Кукуруза для попкорна, 1кг',
                'description': 'Кукуруза для попкорна - это специальный сорт кукурузы, предназначенный для приготовления попкорна.',
                'price': '360 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/bakaleya/specii/05_keshyu_zharenyy_so_speciyami_1kg.jpg',
                'photo_url': '',
            },
        ],
    },
    'Напитки и сладости': {
        'Чай и кофе': [
            {
                'name': 'Кофе молотый "Мехмет Эфенди", оригинальный 100г, 5шт',
                'description': 'Оригинальный турецкий кофе "Мехмет Эфенди", 100г, молотый. Хит продаж.  В комплекте 5 пачки.',
                'price': '560 руб.',
                'weight': '100 г',
                'origin': 'уточняется',
                'photo': 'assets/products/napitki_i_sladosti/chay_i_kofe/01_kofe_molotyy_mehmet_efendi_originalnyy_100g_3sht.jpg',
                'photo_url': '',
            },
            {
                'name': 'Кофе молотый "Мехмет Эфенди", оригинальный 100г, 3шт',
                'description': 'Оригинальный турецкий кофе "Мехмет Эфенди", 100г, молотый. Хит продаж.  В комплекте 3 пачки.',
                'price': '590 руб.',
                'weight': '100 г',
                'origin': 'уточняется',
                'photo': 'assets/products/napitki_i_sladosti/chay_i_kofe/02_kofe_molotyy_mehmet_efendi_originalnyy_100g_5sht.jpg',
                'photo_url': '',
            },
            {
                'name': 'Кофе молотый "Мехмет Эфенди", оригинальный, 100г',
                'description': 'Оригинальный турецкий кофе "Мехмет Эфенди", 100г, молотый. Хит продаж.',
                'price': '620 руб.',
                'weight': '100 г',
                'origin': 'уточняется',
                'photo': 'assets/products/napitki_i_sladosti/chay_i_kofe/03_kofe_molotyy_mehmet_efendi_originalnyy_100g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Цейлонский чёрный чай OPA, крупнолистовой высший сорт, 200г',
                'description': 'Чай крупнолистовой цейлонский OPA',
                'price': '650 руб.',
                'weight': '200 г',
                'origin': 'уточняется',
                'photo': 'assets/products/napitki_i_sladosti/chay_i_kofe/04_ceylonskiy_chernyy_chay_opa_krupnolistovoy_vysshiy_sort_200g.png',
                'photo_url': '',
            },
        ],
        'Сладости': [
            {
                'name': 'Клубника вяленая с сахаром, 500г',
                'description': 'Клубника сушёная, вяленая с сахаром.',
                'price': '460 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/napitki_i_sladosti/chay_i_kofe/01_kofe_molotyy_mehmet_efendi_originalnyy_100g_3sht.jpg',
                'photo_url': '',
            },
            {
                'name': 'Хурма вяленая сушёная, Армения, 1кг',
                'description': 'Хурма вяленая армянская - это натуральный продукт, полученный путем высушивания спелых армянских хурмы без добавления консервантов или других искусственных веществ. Она обладает характерным сладким вкусом и ароматом, который сохраняется благодаря процессу высушивания.\n\nЭтот продукт обычно имеет плотную текстуру с легкими нотками карамели и сушеных фруктов. Хурма вяленая армянская является источником клетчатки и некоторых витаминов и минералов, но содержит также сравнительно высокое содержание сахаров.\n\nХурма вяленая армянская отличается стойкостью к хранению и удобством использования в кулинарии. Она может использоваться в качестве самостоятельной закуски, добавляться в каши, выпечку, салаты, а также в состав различных десертов и сладостей.',
                'price': '490 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/napitki_i_sladosti/chay_i_kofe/02_kofe_molotyy_mehmet_efendi_originalnyy_100g_5sht.jpg',
                'photo_url': '',
            },
            {
                'name': 'Груша сушёная вяленая, 1кг',
                'description': 'Груша вяленая с сахаром',
                'price': '520 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/napitki_i_sladosti/chay_i_kofe/03_kofe_molotyy_mehmet_efendi_originalnyy_100g.jpg',
                'photo_url': '',
            },
            {
                'name': 'Хурма кавказская вяленая (маленькая), 1кг',
                'description': 'Мини-хурма, обыкновенная хурма, кавказская хурма — все названия одного вида хурмы. Выяснено, что в сухих плодах кавказской хурмы содержится до 40% сахаров — в виде глюкозы и фруктозы, что весьма полезно для человеческого организма. Сушёный свежий продукт, имеет косточки.',
                'price': '550 руб.',
                'weight': '1 кг',
                'origin': 'уточняется',
                'photo': 'assets/products/napitki_i_sladosti/chay_i_kofe/04_ceylonskiy_chernyy_chay_opa_krupnolistovoy_vysshiy_sort_200g.png',
                'photo_url': '',
            },
            {
                'name': 'Слива кисло-сладкая сушёная половинки, Армения 500г',
                'description': 'Натуральная слива из Армении, отборная, крупного калибра. Без сахара.',
                'price': '580 руб.',
                'weight': '500 г',
                'origin': 'уточняется',
                'photo': 'assets/products/napitki_i_sladosti/chay_i_kofe/01_kofe_molotyy_mehmet_efendi_originalnyy_100g_3sht.jpg',
                'photo_url': '',
            },
        ],
    },
}


def get_categories() -> list[str]:
    return list(CATALOG.keys())


def get_subcategories(category: str) -> list[str]:
    return list(CATALOG.get(category, {}).keys())


def get_products(category: str, subcategory: str) -> list[Product]:
    return CATALOG.get(category, {}).get(subcategory, [])


def get_product(category: str, subcategory: str, index: int) -> Product | None:
    products = get_products(category, subcategory)
    if 0 <= index < len(products):
        return products[index]
    return None


def find_category_by_subcategory(subcategory: str) -> str | None:
    for category, subcategories in CATALOG.items():
        if subcategory in subcategories:
            return category
    return None


def get_product_ref(product_id: int) -> ProductRef | None:
    current_id = 0
    for category, subcategories in CATALOG.items():
        for subcategory, products in subcategories.items():
            for index, _product in enumerate(products):
                if current_id == product_id:
                    return category, subcategory, index
                current_id += 1
    return None


def get_product_by_id(product_id: int) -> tuple[Product, str, str, int] | None:
    ref = get_product_ref(product_id)
    if ref is None:
        return None
    category, subcategory, index = ref
    product = get_product(category, subcategory, index)
    if product is None:
        return None
    return product, category, subcategory, index


def get_product_id(category: str, subcategory: str, index: int) -> int | None:
    current_id = 0
    for current_category, subcategories in CATALOG.items():
        for current_subcategory, products in subcategories.items():
            for current_index, _product in enumerate(products):
                if (current_category, current_subcategory, current_index) == (category, subcategory, index):
                    return current_id
                current_id += 1
    return None

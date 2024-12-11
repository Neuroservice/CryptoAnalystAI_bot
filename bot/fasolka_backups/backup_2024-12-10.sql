--
-- PostgreSQL database dump
--

-- Dumped from database version 15.10 (Debian 15.10-1.pgdg120+1)
-- Dumped by pg_dump version 15.10

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agentanswer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agentanswer (
    id bigint,
    answer text,
    language text,
    updated_at timestamp with time zone,
    project_id bigint
);


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num text
);


--
-- Name: basic_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.basic_metrics (
    id bigint,
    project_id bigint,
    entry_price double precision,
    sphere text,
    market_price double precision
);


--
-- Name: calculation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.calculation (
    id bigint,
    user_id bigint,
    project_id bigint,
    date timestamp with time zone,
    agent_answer text
);


--
-- Name: funds_profit_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.funds_profit_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: funds_profit; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.funds_profit (
    id bigint DEFAULT nextval('public.funds_profit_id_seq'::regclass),
    project_id bigint,
    distribution text,
    average_price double precision,
    x_value double precision
);


--
-- Name: investing_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.investing_metrics (
    id bigint,
    project_id bigint,
    fundraise double precision,
    fund_level text
);


--
-- Name: manipulative_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.manipulative_metrics (
    id bigint,
    project_id bigint,
    fdv_fundraise double precision,
    top_100_wallet double precision
);


--
-- Name: market_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.market_metrics (
    id bigint,
    project_id bigint,
    fail_high double precision,
    growth_low double precision
);


--
-- Name: network_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.network_metrics (
    id bigint,
    project_id bigint,
    tvl double precision,
    tvl_fdv double precision
);


--
-- Name: project; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project (
    id bigint,
    coin_name text,
    category text
);


--
-- Name: social_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.social_metrics (
    id bigint NOT NULL,
    project_id bigint,
    twitter text,
    twitterscore bigint
);


--
-- Name: tokenomics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tokenomics (
    id bigint,
    project_id bigint,
    circ_supply double precision,
    total_supply double precision,
    capitalization double precision,
    fdv double precision
);


--
-- Name: top_and_bottom; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.top_and_bottom (
    id bigint,
    project_id bigint,
    lower_threshold double precision,
    upper_threshold double precision
);


--
-- Name: user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."user" (
    id bigint,
    telegram_id bigint,
    language text
);


--
-- Data for Name: agentanswer; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agentanswer (id, answer, language, updated_at, project_id) FROM stdin;
2	**Итоговые баллы проекта:** 285.51 баллов – оценка “Отлично”\n\n\n**Положительные характеристики:**\n\n\n- Проект получил высокий балл за Тир проекта (100 баллов), что указывает на значительное финансирование и наличие инвесторов высокого уровня, таких как A16Z и Coinbase Ventures.\n- Проект имеет большое количество подписчиков в Twitter (867K) и высокий Twitter Score (309), что свидетельствует об активном и заинтересованном сообществе. (ссылка на Twitter-аккаунт: https://twitter.com/suinetwork)\n- Проект получил 59 баллов по показателю процента заблокированных токенов, что может способствовать росту цены.\n- Итоговое общее количество баллов проекта составляет 285.51, что указывает на его высокую оценку.\n- Проект получил “Отличную оценку” по показателю прибыльности фондов, что означает, что сообществу крайне нежелательно инвестировать, что может быть положительным для независимого роста токена.\n\n\n**Отрицательные характеристики:**\n\n\n- Проект получил 0 баллов по показателю процента монет на топ 100 кошельках, что может свидетельствовать об отсутствии крупных инвесторов и повышенной волатильности.\n- Проект потерял 5 баллов по показателю роста от минимальных значений и падения от максимальных значений, что может указывать на ограниченный потенциал для дальнейшего роста.	RU	2024-12-04 10:53:03.440539+00	3
3	**Итоговые баллы проекта:** 294.76 баллов – оценка “Отлично”\n\n\n**Положительные характеристики:**\n\n- Проект получил высокий балл по оценке токеномики (101.06 из 100), что свидетельствует о продуманной и устойчивой экономической модели.\n- Проект получил высокие итоговые баллы 294.76.\n- Тир проекта — Тир 1, что указывает на значительное финансирование и наличие инвесторов высокого уровня, таких как Paradigm и Coinbase Ventures.\n- Высокий процент токенов находится на топ 100 кошельках (91%), что может свидетельствовать о наличии крупных инвесторов и стабильности.\n- Низкий процент заблокированных токенов (4.63%), что может способствовать росту цены.\n- Проект получил Хорошую оценку по показателю прибыльности фондов. Сообществу нежелательно инвестировать, что может снизить влияние фондов на цену токенов.\n- Большое количество подписчиков в Twitter (333K) и высокий Twitter Score (152) свидетельствуют об активном и заинтересованном сообществе. (ссылка на Twitter-аккаунт: https://twitter.com/starknet)\n\n\n**Отрицательные характеристики:**\n\n- Баллы по доходности фондов от инвестиций в проект высокие, что может ограничить потенциал дальнейшего роста цены токена.\n- Проект потерял 1 балл по показателю роста от минимальных значений и падения от максимальных значений, что может указывать на нестабильность.\n- Низкий процент токенов находится в заблокированном состоянии (4.63%), что может ограничить доступное предложение.	RU	2024-12-04 11:09:35.985762+00	13
1	Проект Solana (SOL) относится к категории Layer 1 и был запущен в 2020 году. На данный момент общее количество токенов составляет 589,843,195.8090982, из которых в обращении находится 476,115,297.5739695. Последняя известная цена токена составляет 231.29 USD, что на 2.03% ниже по сравнению с предыдущими 24 часами. Solana торгуется на 803 активных рынках, с объемом торгов за последние 24 часа в размере 4,175,613,884.54 USD.\n\nПроект получил 812 баллов в общей оценке, что обусловлено следующими показателями:\n- Сумма сбора средств от инвесторов составила 359,550,000 USD.\n- Количество подписчиков в Twitter — 2.9 миллиона, что также положительно сказалось на Twitter Score, который составил 812.\n\nДополнительные данные показывают, что проект не имеет установленного уровня (Tier) и оценки токемоники. Однако, несмотря на это, Solana демонстрирует значительный интерес со стороны сообщества и инвесторов. \n\nДля более подробной информации можно посетить официальный сайт проекта [Solana](https://solana.com) или их Twitter-аккаунт [Solana в Twitter](https://twitter.com/solana).	RU	2024-12-09 15:10:41.09349+00	151
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.alembic_version (version_num) FROM stdin;
f6ef51cd0375
\.


--
-- Data for Name: basic_metrics; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.basic_metrics (id, project_id, entry_price, sphere, market_price) FROM stdin;
8	8	1.701728011580931	Layer 1	2.5683
9	9	0.7028237111108577	Layer 2 (ETH)	1.1439
10	10	0.5589446479728972	Layer 2 (ETH)	1.052
12	12	0	Layer 2 / GameFi	2.1198
13	13	0.4776593147701949	Layer 2 (ETH)	0.7276
16	16	0	Modular Blockchain	1.6976
17	17	0	Modular Blockchain / GameFi	0.0466
18	18	0	DeFi / Staking / Bridge	0.2703
19	19	0	DeFi / DEX	0.134
21	21	0	DeFi / DEX	1.0849
22	22	0	DeFi / DEX	21.272
23	23	0	DeFi / DEX	0.5474
26	26	0	DeFi / Restaking /Liquid Staking	1.7998
28	28	0	DeFi / DEX	44.0059
31	31	0	DeFi / Liquid Staking (SOL)	3.5934
32	32	0	DeFi / DEX	0.1599
39	39	0	Blockchain Infrastructure / Privacy / ZKP	0.1194
40	40	0	Blockchain Infrastructure / Oracle	0.5129
41	41	0	Blockchain Infrastructure / Developer Tools	0.1873
42	42	0.14681412664555746	Layer 2 (ETH)	0.2308
43	43	0	Blockchain Infrastructure / Cross-Chain	1.0684
44	44	0	Blockchain Infrastructure / Bridge / Cross-Chain	0.3174
45	45	0	Blockchain Infrastructure / Data Service	0.0181
46	46	0	Blockchain Infrastructure / Decentralized Data & Finance Cloud platform 	0.0018
47	47	1.0657456590857854	GameFi / Metaverse	1.93
50	50	0	GameFi / P2E	0.0417
51	51	0	GameFi / Layer 3	0.4079
52	52	0	Metaverse / Marketplace / NFT	0.6582
53	53	0	GameFi / P2E	3.4215
54	54	0	GameFi / Metaverse / P2E	0.2115
55	55	0	GameFi / Metaverse / AI	0.2467
56	56	0	Metaverse / Social	0.0055
57	57	0	GameFi / P2E	0.2766
58	58	0	GameFi / P2E	2.1582
60	60	0	GameFi / P2E	0.0076
65	65	0	Blockchain Service / Social	3.7667
66	66	0	Social / Developer Tools	0.0063
67	67	0	Social / Education	0.4108
68	68	0	Blockchain Service / Social Network / Data Service	0.107
69	69	0	Social / Social Media	0.0014
70	70	0	RWA / Lending	0.2483
73	73	0	AI / NFT	0.0093
75	75	0	AI / DePin / Blockchain Service	490.6907
76	76	0	AI / Bots / Blockchain Service	0.1479
77	77	0	AI / NFT	0.1945
78	78	0	AI / Blockchain Service	0.15
84	84	0	Digital Identity	0.4395
85	85	0	Digital Identity / Blockchain Service	1.9988
86	86	0	Digital Identity	19.2015
87	87	0	Blockchain Service	1.7884
88	88	0	Blockchain Service / Data Service	0.2788
89	89	0	Blockchain Service / DePin	0.0637
90	90	0	Blockchain Service / IoT / DePin	0.1569
91	91	0	Blockchain Service / Data Service / Privacy	0.1061
92	92	0	Digital Identity	2.155
93	93	0	Blockchain Service / Education	0.5092
94	94	0	Digital Identity	0.0253
95	95	0	Blockchain Service / RWA	0.042
96	96	0	Blockchain Service / DePin / IoT	0.0204
97	97	0	Blockchain Service / Browser	0.0134
98	98	0	Digital Identity	0.0512
108	108	2.1	Layer 1	2.1
120	112	\N	DeFi	0.0042
121	147	9.435256858757048	Layer 1	9.4353
122	148	95564.89599398628	Layer 1 (OLD)	95746.6864
123	149	1.1204920826244351	Layer 1	1.4951
124	150	0.12189765306391896	Modular Blockchain	0.1995
126	14	0.3016143659890416	Layer 2 (ETH)	0.7115
127	6	4.930296278314923	GameFi / Metaverse	6.9096
128	7	\N	\N	1.2192
129	20	\N	\N	52.4133
130	24	\N	\N	9.7795
131	25	\N	\N	7.6236
132	27	\N	\N	10.6836
133	29	\N	\N	0.3354
134	61	\N	\N	2.3625
135	62	2.9557067250682113e-05	TON	0
136	63	\N	\N	0.0094
137	64	\N	\N	0.0044
138	71	0.0006079191407021585	Layer 1	0.0008
139	72	\N	\N	0.5879
140	109	\N	\N	0.4269
141	110	\N	\N	1.4557
142	111	\N	\N	0.037
143	113	\N	\N	0.0653
144	114	\N	\N	0.0522
145	115	\N	\N	4658.756
146	116	\N	\N	0.3646
147	117	\N	\N	0.4036
148	118	\N	\N	0.146
149	119	\N	\N	0.0089
150	120	\N	\N	1446.715
151	122	\N	\N	0.0003
152	123	\N	\N	1.7608
153	124	\N	\N	33.1134
154	79	\N	\N	0.4617
155	80	\N	\N	0.1255
156	126	\N	\N	0.3309
157	145	\N	\N	1.4399
158	127	\N	\N	0.3257
159	128	\N	\N	0.5756
49	49	0	GameFi /MEME	0.0168
1	1	12.118678359198249	Layer 1	13.8957
4	4	0	Layer 1	0.0329
15	15	4.7368801383837065	Layer 1	8.4252
125	5	0.10586957857824678	Layer 1	0.1603
160	129	\N	\N	0.3591
161	99	\N	\N	0.0503
162	130	\N	\N	0.0271
163	132	\N	\N	0.0387
164	133	\N	\N	0.0007
165	143	\N	\N	0.9739
166	144	\N	\N	0.1424
167	146	\N	\N	0.2456
168	134	\N	\N	0.3417
169	135	\N	\N	10.2158
170	140	\N	\N	1.2609
171	141	\N	\N	0.3546
172	151	253.9533546216271	Layer 1	231.3782
173	152	3073.37005026452	Layer 2 (ETH)	3711.3568
174	153	\N	Layer 1	\N
175	154	\N	Layer 1 (OLD)	\N
176	155	\N	Layer 1	\N
177	156	\N	Layer 1	\N
178	157	0.07401948311470881	Layer 1	0.0771
179	158	\N	Layer 1	\N
180	159	\N	Layer 1	\N
181	160	608.452991461137	Layer 2 (ETH)	772.0453
182	161	6.010972282476455	Layer 1	6.010972282476455
3	3	3.613336926373536	Layer 1	4.1397
2	2	0	Layer 1	0.7128
\.


--
-- Data for Name: calculation; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.calculation (id, user_id, project_id, date, agent_answer) FROM stdin;
1	833825243	151	2024-11-22 00:30:26.841069+00	**Положительные характеристики:**\n\n- Проект SOL относится к категории "Тир 1 проект", что свидетельствует о высоком уровне проекта.\n- Итоговое общее количество баллов проекта составляет 269.38, что является высоким показателем.\n- Проект имеет большое количество подписчиков в Twitter (2.8M) и высокий Twitter Score (788), что указывает на активное сообщество. (ссылка на Twitter-аккаунт: https://twitter.com/solana)\n- Процент заблокированных токенов (TVL) составляет 7.20%, что может способствовать росту цены.\n\n**Отрицательные характеристики:**\n\n- Проект потерял баллы по показателям доходности фондов, роста от минимума и падения от максимума, а также процента монет на топ 100 кошельков.\n- Оценка токеномики проекта SOL составляет 0.00 баллов, что может указывать на недостаточную привлекательность экономической модели.\n\n**Данные, которые использовались для анализа:**\n- Проект SOL относится к категории "Новые блокчейны 1 уровня (после 2022 года)" на 70% и к категории "Решения 2 уровня на базе Ethereum (ETH)" на 30%.\n- Распределение токенов: Community (34.9%), Seed (14.3%), Team (11.5%), Founding Round (11.3%), Inflation (10.3%), Foundation (10.1%), Validator Round (4.55%), Strategic Round (1.65%), Coinlist Public Sale (1.44%).\n- Рост стоимости токенов с минимума: x2.10.\n- Падение токенов с максимума: -0.02%.\n- Процент нахождения монет на топ 100 кошельков блокчейна: 23.0%.\n- Заблокированные токены (TVL): 7.20%.\n- Сумма привлечения средств: 359,550,000.0.\n- Подписчики в Twitter: 2.8M.\n- Оценка подписчиков твиттера: 788.\n- Оценка токеномики: 0.00 баллов.\n- Оценка доходности фондов: Проект потерял 1 балл.
2	833825243	151	2024-11-22 00:31:29.658938+00	**Положительные характеристики:**\n\n- Проект SOL относится к категории "Тир 1 проект", что свидетельствует о высоком уровне проекта.\n- Итоговое общее количество баллов проекта составляет 269.38, что является высоким показателем.\n- Проект имеет большое количество подписчиков в Twitter (2.8M) и высокий Twitter Score (788), что указывает на активное сообщество. (ссылка на Twitter-аккаунт: https://twitter.com/solana)\n- Процент заблокированных токенов (TVL) составляет 7.20%, что может способствовать росту цены.\n\n**Отрицательные характеристики:**\n\n- Проект потерял баллы по показателям доходности фондов, роста от минимума и падения от максимума, а также процента монет на топ 100 кошельков.\n- Оценка токеномики проекта SOL составляет 0.00 баллов, что может указывать на недостаточную привлекательность экономической модели.\n\n**Данные, которые использовались для анализа:**\n- Проект SOL относится к категории "Новые блокчейны 1 уровня (после 2022 года)" на 70% и к категории "Решения 2 уровня на базе Ethereum (ETH)" на 30%.\n- Распределение токенов: Community (34.9%), Seed (14.3%), Team (11.5%), Founding Round (11.3%), Inflation (10.3%), Foundation (10.1%), Validator Round (4.55%), Strategic Round (1.65%), Coinlist Public Sale (1.44%).\n- Рост стоимости токенов с минимума: x2.10.\n- Падение токенов с максимума: -0.02%.\n- Процент нахождения монет на топ 100 кошельков блокчейна: 23.0%.\n- Заблокированные токены (TVL): 7.20%.\n- Сумма привлечения средств: 359,550,000.0.\n- Подписчики в Twitter: 2.8M.\n- Оценка подписчиков твиттера: 788.\n- Оценка токеномики: 0.00 баллов.\n- Оценка доходности фондов: Проект потерял 1 балл.
3	833825243	151	2024-11-22 00:32:54.400446+00	\N
4	833825243	151	2024-11-22 00:35:44.152203+00	\N
5	833825243	151	2024-11-22 00:35:45.18443+00	\N
6	833825243	3	2024-11-22 00:36:32.6484+00	**Положительные характеристики:**\n\n- Проект SUI получил высокие итоговые баллы 274.80.\n- Проект относится к Тир 1, что свидетельствует о высоком уровне финансирования и привлекательности для инвесторов.\n- Проект имеет значительное финансирование в размере 385 370 000,00 долларов.\n- Высокий процент заблокированных токенов (16.08%) может способствовать росту цены.\n- Большое количество подписчиков в Twitter (839K) и высокий Twitter Score (308) указывают на активное и заинтересованное сообщество. (ссылка на Twitter-аккаунт: https://twitter.com/suinetwork)\n\n**Отрицательные характеристики:**\n\n- Проект потерял баллы по показателям доходности фондов, роста от минимумов и падения от максимумов, а также процента монет на топ 100 кошельков.\n- Оценка токеномики проекта равна 0.00 баллов.\n- Проект не получил баллов по оценке токеномики.\n- Проект потерял 1 балл по показателю доходности фондов.\n\n**Данные, которые использовались для анализа:**\n*Проект SUI относится:*\n- на 70% к категории "Новые блокчейны 1 уровня (после 2022 года)"\n- на 30% к категории "Решения 2 уровня на базе Ethereum (ETH)"\nОбщая категория проекта: "Новые блокчейны 1 уровня (после 2022 года)".\n\nРаспределение токенов: \nРост стоимости токенов с минимума: x4.857714762273056\nПадение токенов с максимума (%): -0.08636031760038076%\nПроцент нахождения монет на топ 100 кошельков блокчейна: 16.0%\nЗаблокированные токены (TVL, %): 16.08481630083385%\nСумма привлечения средств: 385 370 000,00\nУровень проекта: Тир 1\nПодписчики в Twitter: 839K\nОценка подписчиков твиттера: 308\nОценка токеномики (сравнение с другими проектами): 0.00\nОценка доходности фондов: Проект потерял 1 балл.
7	833825243	3	2024-11-22 00:36:58.430578+00	\N
8	833825243	151	2024-11-22 00:40:19.784688+00	\N
9	833825243	151	2024-11-22 00:50:07.671202+00	**Положительные характеристики:**\n\n- Проект SOL относится к категории "Тир 1 проект", что свидетельствует о высоком уровне проекта.\n- Итоговое общее количество баллов проекта составляет 269.38, что является высоким показателем.\n- Проект имеет большое количество подписчиков в Twitter (2.8M) и высокий Twitter Score (788), что указывает на активное сообщество. (ссылка на Twitter-аккаунт: https://twitter.com/solana)\n- Процент заблокированных токенов (TVL) составляет 7.20%, что может способствовать росту цены.\n\n**Отрицательные характеристики:**\n\n- Проект потерял баллы по показателям доходности фондов, роста от минимума и падения от максимума, а также процента монет на топ 100 кошельков.\n- Оценка токеномики проекта SOL составляет 0.00 баллов, что может указывать на недостаточную привлекательность экономической модели.\n\n**Данные, которые использовались для анализа:**\n- Проект SOL относится к категории "Новые блокчейны 1 уровня (после 2022 года)" на 70% и к категории "Решения 2 уровня на базе Ethereum (ETH)" на 30%.\n- Распределение токенов: Community (34.9%), Seed (14.3%), Team (11.5%), Founding Round (11.3%), Inflation (10.3%), Foundation (10.1%), Validator Round (4.55%), Strategic Round (1.65%), Coinlist Public Sale (1.44%).\n- Рост стоимости токенов с минимума: x2.10.\n- Падение токенов с максимума: -0.02%.\n- Процент нахождения монет на топ 100 кошельков блокчейна: 23.0%.\n- Заблокированные токены (TVL): 7.20%.\n- Сумма привлечения средств: 359,550,000.0.\n- Подписчики в Twitter: 2.8M.\n- Оценка подписчиков твиттера: 788.\n- Оценка токеномики: 0.00 баллов.\n- Оценка доходности фондов: Проект потерял 1 балл.
10	833825243	13	2024-11-30 23:52:06.871006+00	\N
11	833825243	13	2024-11-30 23:52:43.232331+00	\N
12	833825243	13	2024-11-30 23:54:44.154238+00	\N
13	833825243	13	2024-11-30 23:57:32.817967+00	**Итоговые баллы проекта:** 193,70 баллов – оценка “Хорошо”\n\n\n**Положительные характеристики:**\n\n\n- Проект получил высокий балл за Тир проекта (100 баллов), что указывает на значительное финансирование и наличие инвесторов высокого уровня.\n- Проект имеет большое количество подписчиков в Twitter (333K), что свидетельствует об активном и заинтересованном сообществе. (ссылка на Twitter-аккаунт: https://twitter.com/starknet)\n- Проект получил Плохую оценку по показателю прибыльности фондов, что позволяет сообществу инвестировать без значительного влияния фондов на цену токенов.\n- Проект получил 56,50 баллов за привлеченные инвестиции, что также является положительным показателем.\n\n\n**Отрицательные характеристики:**\n\n\n- Проект получил 0 баллов по оценке токеномики, что может свидетельствовать о недостаточной продуманности экономической модели.\n- Низкие баллы по показателю процента заблокированных монет (14 баллов), что может указывать на высокую ликвидность и потенциальную волатильность.\n- Проект потерял 1 балл по показателю роста от минимальных значений, что может ограничить потенциал дальнейшего роста цены токена.\n\n**Данные для анализа**\n- Анализ категории: ```\nПроект StarkNet относится:\n\n\n- на 100% к категории "Решения 2 уровня на базе Ethereum"\n- на 10% к категории "Децентрализованные финансы"\n\n\nПо остальным категориям признаков не обнаружено.\nОбщая категория проекта: "Решения 2 уровня на базе Ethereum".\n```\n\n- Тикер монеты: STRK\n- Категория: Layer 2 (ETH)\n- Цена токена: $0.47766\n- Капитализация: $1002824272.52\n- Фандрейз: $282500000\n- Количество подписчиков: 333K (Twitter: https://twitter.com/starknet)\n- Twitter Score: 152\n- Тир фондов: Paradigm (TIER 1+), Coinbase Ventures (TIER 1+), Multicoin Capital (TIER 1+), Pantera capital (TIER 1), Sequoia Capital (TIER 1),  ConsenSys (TIER 2+), Ethereum Foundation + Vitalik Buterin\n- Распределение токенов: StarkWare Investors(17%)\nCore Contributors(32.9%)\nCommunity Provisions(9%)\nCommunity Rebates(9%)\nresearch and development(12%)\na strategic reserve(10%)\nDonations(2%)\nUnallocated(8.1%)\n- Минимальная цена токена: $0.32\n- Максимальная цена токена: $0.52%\n- Рост стоимости токена с минимума: $1.85\n- Рост стоимости токена с минимума: 1.85%\n- Падение стоимости токена с максимума: -0.28%\n- Процент нахождения монет на топ 100 кошельков блокчейна: 91.0%\n- Заблокированные токены (TVL): 14%\n\n- Токенов в обращении: 2099455075.0\n- Общее число токенов: 10000000000.0\n- FDV: 3423948354.7916346\n- FDV/Fundraise: 16.52\n- TVL/FDV: 0.03\n- Тир проекта: Проект STRK относится к категории 'Тир 1 проект'.\n- Оценка доходности фондов: ```\nПроект получил “Плохую оценку. Сообщество может инвестировать” по показателю доходности фондов.\nПроект потерял 1 балл по показателю роста от минимальных значений и падения от максимальных значений.\nПроект получил 21 балл по показателю процента монет на топ 100 кошельков.\nПроект получил 14 баллов по показателю процента заблокированных монет.\n```\n- Оценка токеномики: Общая оценка проекта STRK: 0 + 0 + 0 + 0 + 0 + 0 = **0.00** баллов.\n\nОтдельные набранные баллы в сравнении с другими проектами:\n- OP = 0 баллов,\n- ARB = 0 баллов,\n- MNT = 0 баллов,\n- IMX = 0 баллов,\n- POL = 0 баллов,\n- ZK = 0 баллов.\n\n**Данные для анализа токеномики**:\nВариант 1\nРезультаты расчета для STRK в сравнении с OP:\nВозможный прирост токена (в %): 1.91363%\nОжидаемая цена токена: 0.91406\n\nВариант 2\nРезультаты расчета для STRK в сравнении с ARB:\nВозможный прирост токена (в %): 1.64411%\nОжидаемая цена токена: 0.78533\n\nВариант 3\nРезультаты расчета для STRK в сравнении с MNT:\nВозможный прирост токена (в %): 1.10448%\nОжидаемая цена токена: 0.52756\n\nВариант 4\nРезультаты расчета для STRK в сравнении с IMX:\nВозможный прирост токена (в %): 0.56799%\nОжидаемая цена токена: 0.27130\n\nВариант 5\nРезультаты расчета для STRK в сравнении с POL:\nВозможный прирост токена (в %): 1.03287%\nОжидаемая цена токена: 0.49336\n\nВариант 6\nРезультаты расчета для STRK в сравнении с ZK:\nВозможный прирост токена (в %): 0.65985%\nОжидаемая цена токена: 0.31518\n\n
14	833825243	161	2024-12-01 14:25:41.29972+00	\N
15	833825243	161	2024-12-01 14:41:42.684337+00	\N
16	833825243	161	2024-12-01 14:44:18.010346+00	\N
17	833825243	161	2024-12-01 14:46:06.701352+00	\N
18	833825243	148	2024-12-03 21:38:35.326537+00	\N
19	833825243	148	2024-12-03 21:39:54.081368+00	\N
20	833825243	148	2024-12-03 21:40:32.458702+00	\N
\.


--
-- Data for Name: funds_profit; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.funds_profit (id, project_id, distribution, average_price, x_value) FROM stdin;
1	1	Community (45.5%)\nCore Contributors (16.9%)\nFoundation (14.7%)\nInvestors (12%)\nStaking Rewards (10.8%)\nStaking Rewards (-)	2.32	3.33
2	2	Private Sale Investors(20%)\nBinance Launchpool(3%)\nTeam(20%)\nFoundation(9%)\nEcosystem Reserve(48%)	\N	\N
3	3	Allocated After 2030 (52.2%)\nCommunity Reserves (10.6%)\nStake Subsidies (9.49%)\nSeries A (7.14%)\nSeries B (6.96%)\nEarly Contributors (6.13%)\nCommunity Access Program (5.82%)\nMysten Labs Treasury (1.64%)	\N	\N
4	4	Community(58.3%)\nTeam, advisors & backers(19.2%)\nFlare entities(22.5%)	0	3.26
8	8	Ecosystem Fund(25%)\r\nRetroactive Public Goods Funding(20%)\r\nUser airdrops(19%)\r\nCore contributors(19%)\r\nSugar xaddies(17%)	0.24	7.47
9	9	DAO Treasury (35.3%)\nTeam & Advisors (26.9%)\nInvestors (17.5%)\nAirdrop (11.6%)\nArbitrum Foundation (7.50%)\nDAOs in Arbitrum Ecosystem (1.13%)	0.07	8.87
10	10	Circulating(51%) Mantle Treasury(49%)	\N	\N
12	12	Ecosystem Development(51.7%) Project Development(25%) Private Sales(13.9%) Foundation Reserve(4%) Public Sales 1(2.9%) Public Sales 2(2.5%)	1.11	1.54
13	13	StarkWare Investors(17%)\nCore Contributors(32.9%)\nCommunity Provisions(9%)\nCommunity Rebates(9%)\nresearch and development(12%)\na strategic reserve(10%)\nDonations(2%)\nUnallocated(8.1%)	0.16	3.01
15	15	R&D & Ecosystem(26.8%) Series A&B(19.7%) Initial Core Contributors(17.6%) Seed(15.9%) Other(20%)	0.29	19.83
16	16	Public allocation(8%)\nEcosystem and R&D(20%)\nIncentives Manager(33%)\nCommunity Pool(5%)\nBackers(14%)\nCore Contributing Team(20%)	0.05	39.36
17	17	Ecosystem Fund(22%) Community Fund(22%) Seed Round(14.8%) Foundation(14%) Other(27.2%)	\N	\N
18	18	Community(30.39%) Investors(17.5%) Team(17.5%) Bonding Curve(15.95%) Other(18.66%)	0.14	2.33
19	19	Core Team(19.32%)\nEarly Investors(25%)\nFuture Hires(2.5%)\nEcosystem Development(53.18%)	0.12	1.33
21	21	Team(40%) Community(35%) Initial Airdrop(10%) Other Liquidity Needs(5.5%) Community Needs(5%) Launch Pool(2.5%) Active Staking Rewards(0.5%) Launchpad Fee(0.5%) MM Loans(0.5%) Immediate LP Needs(0.5%)	\N	\N
22	22	XVIX & Gambit Migration(45.3%) Luquidity(15.1%) Floor Price Fund(15.1%) Reverse(15.1%) Marketing & Partnerships(7.54%) Contributors(1.88%)	\N	\N
23	23	Staking Rewards(25%)\nDeveloper Vesting(25%)\nLiquidity Mining Incentives(45%)\nCommunity Pool(5%)	\N	\N
26	26	Investors(32.5%) DAO Treasury(23.3%) Core Contributors(23.3%) Airdrop Season 1(6%) Airdrop Season 2(5.8%) Liquidity(3%) Binance Launchpool(2%) Protocol Guild(1%)	0.1	18.29
28	28		\N	\N
31	31	Ecosystem Development(25%) Core Contributors(24.5%) Community Grouth(24.3%) Investors(16.2%) Airdrop(10%)	0.09	26.75
32	32	Liquidity Mining and Airdrops(30.9%) Team(19%) Investors(18%) Public Good Fund(16.5%) Foundation / Treasury(10%) Advisors(4.15%) Binance Launchpool(1.5%)	0.05	4.63
39	39	Team(20%)\nBackers(36.5%)\nCoinList Sale(7.5%)\nMix-Mining(25%)\nReserve & Community(11%)	0.12	0.67
40	40	0.1	\N	\N
41	41	Binance Launchpool(5%)\nTeam(15%)\nInvestors(18.5%)\nAdvisors(5%)\nProtocol Development(20%)\nEcosystem and Community(15%)\nTreasury(21.5%)	0.02	6.63
42	42	0.28	0.18	6.43
43	43	Team(17%)\nCompany Operations(12.5%)\nCommunity Sale(5%)\nCommunity Programs(36%)\nBackers(29.5%)	\N	\N
44	44	\N	\N	\N
45	45	0.32	0.04	0.62
46	46	0.21	0.06	0.05
47	47		\N	\N
49	49	0.12	0	6.36
50	50	0.27	0.05	0.86
51	51	0.21	0.04	6.33
52	52	Treasure Farm(33%)\nMining(25%)\nStaking/Liquidity(17%)\nEcosystem Fund(15%)\nTeam(10%)	\N	\N
53	53	0.23	0.2	12.41
54	54	-)	\N	\N
55	55	0.2	0.02	7.48
56	56	0.06	0.02	0.26
57	57	0.14	0.01	15.41
58	58	0.15	0.21	7.48
60	60	0.25	0.01	1.06
65	65	Team & Advisors(15%)\nPrivate Sale(25.12%)\nCommunity Treasury(10.88%)\nCommunity Rewards(12%)\nCoinList Public Sale(3%)\nEcosystem Development(34%)	1	3.6
66	66	0.28	0.03	0.37
67	67	0.2	\N	\N
68	68	0.15	0.07	2.09
69	69	0.07	0	9.07
70	70	0.12	0.05	2.74
73	73	0.23	\N	\N
75	75	\N	\N	\N
76	76	\N	\N	\N
77	77	0.1	0.06	3.57
78	78	\N	\N	\N
84	84	0.28	0.02	22.46
85	85	0.17	0.07	22.92
86	86	-)	\N	\N
87	87	0.21	1.22	1.88
88	88	0.3	0.04	6.12
89	89	0.2	0.02	3.99
90	90	0.08	0.27	0.6
91	91	0.24	0.09	1.33
92	92	0.1	0.25	7.68
93	93	0.13	0.07	8.98
94	94	0.08	0.93	0.05
95	95	\N	\N	\N
96	96	0.09	0.01	2.66
97	97	0.09	0.01	2.52
98	98	0.17	0.1	0.5
99	152		\N	\N
100	151	Community (34.9%)\nSeed (14.3%)\nTeam (11.5%)\nFounding Round (11.3%)\nInflation (10.3%)\nFoundation (10.1%)\nValidator Round (4.55%)\nStrategic Round (1.65%)\nCoinlist Public Sale (1.44%)	\N	\N
101	149		\N	\N
102	6		\N	\N
103	71		\N	\N
104	5	-)	\N	\N
\.


--
-- Data for Name: investing_metrics; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.investing_metrics (id, project_id, fundraise, fund_level) FROM stdin;
1	1	350000000	A16Z (TIER 1+), Coinbase Ventures (TIER 1+), Binance Labs (TIER 1+), Multicoin Capital (TIER 1+), DragonFly Capital (TIER 1), Hashed Fund (TIER 1), Circle (TIER 2+)
2	2	85000000	Multicoin Capital (TIER 1+), Coinbase Ventures (TIER 1+), Circle (TIER 2+), Jump Crypto (TIER 2), Delphi Digital (TIER 2), GSR (TIER 3)
3	3	385370000	A16Z (TIER 1+), Coinbase Ventures (TIER 1+), Binance Labs (TIER 1+), Circle (TIER 2+), Electric capital (TIER 3)
4	4	46300000	Digital Currency Group (TIER 1+), Kenetic Capital (TIER 2+), CoinFund (TIER 2), LD Capital (TIER 2)
8	8	178500000	A16Z (TIER 1+), Paradigm (TIER 1+), IDEO colab ventures (TIER 3)
9	9	123700000	Polychain Capital (TIER 1+), Pantera capital (TIER 1), Lightspeed Venture Partners (TIER 3), 
10	10	0	-
12	12	308420000	Coinbase Ventures (TIER 1+), Arrington Capital (TIER 1), Animoca Brands (TIER 2+), Galaxy (TIER 2+), Fabric ventures (TIER 2+), ParaFi Capital (TIER 2)
13	13	282500000	Paradigm (TIER 1+), Coinbase Ventures (TIER 1+), Multicoin Capital (TIER 1+), Pantera capital (TIER 1), Sequoia Capital (TIER 1),  ConsenSys (TIER 2+), Ethereum Foundation + Vitalik Buterin
15	15	111590000	Binance Labs (TIER 1+), Coinbase Ventures (TIER 1+), Polychain Capital (TIER 1+), Blockchain Capital (TIER 1), The Spartan Group (TIER 2+), Galaxy (TIER 2+)
16	16	6700000	Big brain, Stratos, Matchbox
17	17	0	-
18	18	25000000	Alameda
19	19	30950000	Coinbase Ventures (TIER 1+), DragonFly Capital (TIER 1), Arrington Capital (TIER 1), Fabric ventures (TIER 2+), Galaxy (TIER 2+), Morningstar ventures (TIER 2), Electric capital (TIER 3), Jump crypto (TIER 3), Wintermute (TIER 3)
21	21	0	-
22	22	10500000	Arbitrum Foundation (TIER 3)
23	23	21000000	Paradigm (TIER 1+), Robot Ventures (TIER 3), Nascent (TIER 3), Figment Capital (TIER 4), Ethereal Ventures (TIER 4)
26	26	32300000	Arrington capital (TIER 1), ConsenSys (TIER 2+), CoinFund (TIER 2), Sandeep Nailwal (TIER 1 - ангел), Stani Kulechov (TIER 2 - ангел), OKX (TIER 3+)
28	28	0	-
31	31	14200000	Multicoin Capital (TIER 1+), Delphi Digital (TIER 3), Robot Ventures (TIER 3), Solana ventures (TIER 3), Framework ventures (TIER 4)
32	32	17460000	Binance Labs (TIER 1+), Coinbase Ventures (TIER 1+),  Pantera capital (TIER 1), Shima Capital (TIER 2+), The Spartan Group (TIER 2+), Circle (TIER 2+), Jump crypto (TIER 3) и другие слабые фонды
39	39	42925000	A16Z (TIER 1+), Digital Currency Group (TIER 1+), Polychain Capital (TIER 1+), Binance Labs (TIER 1+), HashKey Capital (TIER 1)
40	40	0	Multicoin Capital (TIER 1+), Galaxy (TIER 2+), CMS Holdings (TIER 2), Jump Trading (TIER 3), DWF Labs (TIER 3), Delphi Digital (TIER 3), CMT Digital (TIER 3), Wintermute (TIER 3), Distributed Global (TIER 3), GBV capital (TIER 3)  и другие низшие фонды
41	41	37200000	Polychain Capital (TIER 1+), Binance Labs (TIER 1+),HashKey Capital (TIER 1), IOSG (TIER 2), Jump crypto (TIER 3), Hack VC (TIER 3)
42	42	45000000	Polychain Capital (TIER 1+), Binance Labs (TIER 1+), HashKey Capital (TIER 1), Animoca Brands (TIER 2+), NGC Ventures (TIER 2+)
43	43	63800000	Coinbase Ventures (TIER 1+), Polychain Capital (TIER 1+), Binance Labs (TIER 1+), DragonFly Capital (TIER 1), Galaxy (TIER 2+), RockawayX (TIER 2+), Morningstar ventures (TIER 2) и другие tier 3 фонды
44	44	10000000	Placeholder Ventures (TIER 2), Blockchain Capital (TIER 3), Hack VC (TIER 3)
45	45	12800000	Coinbase Ventures (TIER 1+), IOSG (TIER 2), CMS Holdings (TIER 2), Mechanism capital (TIER 3), D1 ventures (TIER 3), Hypersphere ventures (TIER 3) и другие слабые фонды
46	46	116200000	Binance Labs (TIER 1+), Arrington Capital (TIER 1), Kenetic Capital (TIER 2+), Fenbushi Capital (TIER 2), LD Capital (TIER 2) + неизвестные инвестора (N/A) и инвестора низшего TIER-a
47	47	\N	A16Z (TIER 1+), Coinbase Ventures (TIER 1+), Hashed Fund (TIER 1), Animoca Brands (TIER 2+), Standard Crypto (TIER 2)
49	49	15870000	Binance Labs (TIER 1+)
50	50	38100000	Polychain Capital (TIER 1+), DragonFly Capital (TIER 1), IOSG (TIER 2), Franklin Templeton (tier 3), Brevan Howard (TIER 3), Tess ventures (TIER 3)
51	51	10000000	Animoca Brands (TIER 2+), CMS Holdings (TIER 2) и другие слабые фонды
52	52	3000000	Merit Circle (TIER 2), 1kx (TIER 3), другие фонды, низших категорий
53	53	6600000	Binance Labs (TIER 1+), Morningstar ventures (TIER 2), FunPlus (TIER 4)
54	54	10300000	Digital Currency Group (TIER 1+), Circle (TIER 2+), OKX (TIER 3), Sound Ventures (TIER 4), North Island Ventures (TIER 4)
55	55	14000000	Polygon (TIER 3), Galaxy Interactive (TIER 3), Ancient8 (TIER 3), GSR (TIER 3), Formless capital (TIER 3) и другие фонды низшего ранга
56	56	13000000	Jump crypto (TIER 3), Collab+Currency (TIER 3), Everest ventures (TIER 4), Parataxis Capital (TIER 4), MZ Web3 Fund (TIER 4)
57	57	7200000	Animoca Brands (TIER 2+), Fenbushi Capital (TIER 2), Mechanism capital (TIER 3), Collab+Currency (TIER 3), Yield guild games (TIER 3) и другие фонды низшего ранга
58	58	8000000	Binance Labs (TIER 1+), HashKey Capital (TIER 1), Animoca Brands (TIER 2+), Merit Circle (TIER 2), Delphi Digital (TIER 3), Genblock capital (TIER 3), Mechanism capital (TIER 3)
60	60	10000000	Animoca Brands (TIER 2+), Merit Circle (TIER 2), Fenbushi Capital (TIER 2), Rarestone Capital (TIER 3),  и другие фонды низшего ранга
65	65	25100000	Binance Labs (TIER 1+), Multicoin Capital (TIER 1+), Hashed Fund (TIER 1), Animoca Brands (TIER 2+), The Spartan Group (TIER 2+), IOSG (TIER 2)
66	66	7000000	Digital Currency Group (TIER 1+), HashKey Capital (TIER 1), Animoca Brands (TIER 2+), Morningstar ventures (TIER 2), GBV capital (TIER 3)
67	67	6000000	Binance Labs (TIER 1+), Sequoia Capital (TIER 1)
68	68	10000000	Coinbase Ventures (TIER 1+), DragonFly Capital (TIER 1), HashKey Capital (TIER 1), Fabric ventures (TIER 2+), SevenX ventures (TIER 3), Continue Capital (TIER 3) и множество других фондов низшего ранга
69	69	1200000	CMS Holdings (TIER 2), Sora ventures (TIER 3), Double Peak (TIER 4), DV Chain (TIER 4)
70	70	6150000	Sequoia Capital (TIER 1), Arrington Capital (TIER 1), HashKey Capital (TIER 1), Kenetic Capital (TIER 2+), Wintermute (TIER 3), GBV capital (TIER 3), FBG Capital (TIER 3), Sino Global Capital (TIER 3)
73	73	19000000	Multicoin Capital (TIER 1+),NGC Ventures (TIER 2+), The Spartan Group (TIER 2+), IOSG (TIER 2), CMS Holdings (TIER 2), LD Capital (TIER 2), Galaxy interactive (TIER 3), BITkraft ventures (TIER 3), IDEO colab ventures (TIER 3), Sfermion (TIER 3)
75	75	0	-
76	76	0	-
77	77	6000000	Binance Labs (TIER 1+)
78	78	0	-
84	84	10000000	Binance Labs (TIER 1+), Polychain Capital (TIER 1+), dao5 (TIER 5)
85	85	12000000	Binance Labs (TIER 1+), Coinbase Ventures (TIER 1+), Digital Currency Group (TIER 1+)
86	86	1000000	Ethereum Foundation (TIER 4), Chainlink (TIER 4), Protocol Labs (TIER 4)
87	87	20640000	Coinbase Ventures (TIER 1+), Multicoin Capital (TIER 1+), Binance Labs (TIER 1+), DragonFly Capital (TIER 1), HashKey Capital (TIER 1), The Spartan Group (TIER 2+), Shima Capital (TIER 2+) и другие фонды низшего ранга
88	88	12200000	Binance Labs (TIER 1+), Coinbase Ventures (TIER 1+), Fenbushi Capital (TIER 2), Morningstar ventures (TIER 2), CoinFund (TIER 2), Eden block (TIER 3), Mechanism capital (TIER 3), Genblock capital (TIER 3) и другие фонды низшего ранга
89	89	21000000	Multicoin Capital (TIER 1+), Solana ventures (TIER 3), Google Ventures (TIER 3) и другие фонды низшего ранга
90	90	20500000	Variant (TIER 2+), CoinFund (TIER 2), Slow ventures (TIER 3) и другие фонды низшего ранга
91	91	23000000	A16Z (TIER 1+), Coinbase Ventures (TIER 1+), Digital Currency Group (TIER 1+), Blockchain Capital (TIER 1) и другие фонды низшего ранга
92	92	240000000	A16Z (TIER 1+), Digital Currency Group (TIER 1+), Multicoin Capital (TIER 1+), Coinbase Ventures (TIER 1+), Hashed Fund (TIER 1), Variant (TIER 2+), Kenetic Capital (TIER 2+), CoinFund (TIER 2)
93	93	9150000	Binance Labs (TIER 1+)
94	94	40000000	DWF Labs (TIER 3), Ticker Capital (TIER 5)
95	95	10000000	DWF Labs (TIER 3)
96	96	1150000	DWF Labs (TIER 3)
97	97	600000	-
98	98	11730000	Binance Labs (TIER 1+), DAO Maker (TIER 3), Protocol Labs (TIER 4)
99	152	18300000	\N
100	151	359550000	-
101	149	\N	\N
102	6	\N	\N
103	71	22010000000	\N
104	5	0	-
\.


--
-- Data for Name: manipulative_metrics; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.manipulative_metrics (id, project_id, fdv_fundraise, top_100_wallet) FROM stdin;
1	1	43.103737168636606	0.14
4	4	32.62	\N
8	8	58.76939926529555	0.88
9	9	77.87408683662623	0.6
10	10	\N	1
12	12	7.324058001491372	\N
13	13	16.52	0.91
16	16	281.17	\N
17	17	\N	0.4
18	18	13.33	1
19	19	5.31	0.94
21	21	\N	0.95
22	22	23.11	0.96
23	23	26.008346836211153	0.78
26	26	56.27	0.98
28	28	\N	1
31	31	167.42973242691937	0.97
32	32	25.7	1
39	39	2.780438746062373	0.73
40	40	\N	0.91
41	41	29.975422240481446	0.99
42	42	22.98	0.98
43	43	13.067036388194579	0.88
44	44	27.13	0.97
45	45	1.96	\N
46	46	0.24	0.94
47	47	\N	\N
50	50	3.17	0.96
51	51	55.443310011082914	0.89
52	52	76.28700210888134	1
53	53	55.14	0.98
54	54	102.69048005859395	0.97
55	55	52.41436433337828	0.98
56	56	4.75	0.99
57	57	192.07909279412752	1
58	58	49.84	0.98
60	60	4.22	0.99
65	65	12.48195854286111	0
66	66	1.36	0.97
67	67	32.82054012364542	0.98
68	68	10.703416519723204	0.98
69	69	120.98	0.86
70	70	40.38191105373591	0.82
73	73	0	0.96
75	75	\N	\N
76	76	\N	0.7
77	77	35.75	0.99
78	78	\N	0.56
84	84	88.21230737210153	1
85	85	166.56368624441515	0.9
86	86	1740.6955556380135	0.9
87	87	9.07	0.99
88	88	22.849783681278243	0.97
89	89	19.38670037455571	0.59
90	90	7.87	1
91	91	5.43	0.92
92	92	82.58483470395613	0.96
93	93	55.67004661790142	1
94	94	0.58	0.97
95	95	58.61	0.95
96	96	28.95	0.97
97	97	29.67	0.9
98	98	2.5875454256266615	0.97
99	152	21825.884189174027	0.65
100	151	265.10058476987786	0.23
101	149	\N	\N
102	6	\N	\N
103	71	0.015191073484152075	\N
104	5	\N	0.33
105	172	388.70482780544427	0.23
106	173	24305.17459081139	0.67
49	49	72.84606745828646	0.96
3	3	107.42093133535889	0.16
15	15	82.12092356005572	0.97
2	2	83.86412698375861	1
\.


--
-- Data for Name: market_metrics; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.market_metrics (id, project_id, fail_high, growth_low) FROM stdin;
1	1	-0.018456755010290204	2.6580856042609695
2	2	-0.009633201137019154	2.842333023535982
3	3	-0.06895091908007411	4.7101956967760685
4	4	-0.2585363376053227	1.051725515027816
8	8	-0.020965321228219702	2.0325033362244254
9	9	-0.03571317188272305	2.3965641325028213
10	10	-0.34	2.05
12	12	-0.017533648168276628	2.162964081821309
13	13	-0.2792285048549624	1.1853897935277555
15	15	-0.0460363067535986	2.289615330353474
16	16	-0.19392510193554424	1.5022953409944637
17	17	29.31814845608041	67.27051923200533
18	18	-0.324984499015187	1.0523305104881961
19	19	-0.3361969995503633	1.197099602240721
20	20	-0.016337025472265454	2.642153331482943
21	21	1.9663210955679036	5.001643249622007
22	22	-0.4205381939519748	1.204532440544904
23	23	-0.2050826461004127	1.5436550758467449
24	24	-0.2843404151271761	1.222782601968136
25	25	-0.27977377154018623	1.3762970646576025
26	26	-0.12503127842144424	1.501093127845779
27	27	-0.0050477548352786394	3.160947274657487
28	28	52.3957021577437	146.60065556832475
29	29	-0.17635421836092846	2.530532193281543
30	30	-1	0
31	31	-0.036099991793150155	1.9974537135048007
32	32	-0.38849340090917006	1.3821000489390842
33	33	-0.84	0.4
34	34	-0.83	0.58
35	35	-0.99	0.88
36	36	-1	0.07
37	37	-0.99	0.85
39	39	-0.3436077525218314	1.7581935200308088
40	40	-0.03881459484364658	2.1881801075411307
41	41	-0.26104326882312145	1.5659116800251507
42	42	-0.1750340282252959	1.6282765867903222
43	43	-0.23109711513674525	1.5386415337317956
44	44	0.32	8.22
45	45	-0.3843585292484647	1.0117545375911114
46	46	-0.5418432239422455	1.015801938898652
47	47	-0.06681138870257941	3.287228142717673
49	49	-0.02953057543211024	1.9439865323892453
50	50	-0.3002402461554139	2.3029089635084112
51	51	-0.40165755539723635	1.1267487593168926
52	52	-0.3079794637054952	1.3073154372409643
53	53	-0.4160836995112992	1.1089557219253554
54	54	-0.10039897508671769	3.299721256326818
55	55	-0.577391032701061	2.245784833791997
56	56	-0.37338143101294596	1.175043481221244
57	57	-0.01933549474783902	2.5157683067599605
58	58	-0.3261754638336821	1.251199677940202
60	60	-0.9216034601883855	0.0786323555625259
65	65	-0.22686634434622344	1.424624497104841
66	66	-0.7125813118015603	1.1291263143524188
67	67	-0.21902443332764454	1.2841298783046544
68	68	-0.3276748417259294	1.113199846045055
69	69	-0.28074032080182	1.059013145938072
70	70	-0.21134089240877785	2.19972323277658
73	73	-0.3305435651938118	1.1734821484046192
75	75	-0.9999542969971406	0.00018995040644637686
76	76	-0.8954093146378006	0.24209452346075522
77	77	-0.36095005633501887	1.1537770038648887
78	78	2045.2496532992882	5833.222383038152
84	84	2.784821501482639	6.487387974466023
85	85	-0.21739849846006976	2.2402647780015488
86	86	-0.16369839204363734	1.318783304854264
87	87	-0.4271677470124392	1.141277788019888
88	88	-0.10421799192932324	1.6622979183756388
89	89	-0.3578325130600385	1.3114167131974899
90	90	-0.3103917804785802	1.3642249560097655
91	91	-0.41031483207115593	1.0200419395230678
92	92	-0.24518872753637677	1.6362841176033747
93	93	-0.3089350926066333	1.203606074824325
94	94	-0.9589895770252308	1.135970326076902
95	95	-0.47337244803262746	1.1928323268455074
96	96	-0.6152928227891576	1.2243824232788185
97	97	-0.5626319095891935	1.096459987898228
98	98	26.47064643943075	56.30321788543611
99	5	-0.1532580717584685	1.6153618333417312
100	14	-0.06531845188120222	2.5135532171730106
101	6	-0.01644836285802831	1.589085783948696
102	7	-0.09861524813794798	3.941145191831773
103	61	-0.10479657435120915	1.4019822948270768
104	63	-0.09979988101919735	1.723994113854621
105	109	-0.04974217460307684	2.7944665877351595
106	110	-0.6372815390258445	2.215006665421575
107	111	-0.23180146732032636	1.4517790844378282
108	112	-0.4886886944232215	1.5040366443776734
109	113	-0.3027318258316206	1.3034454218797449
110	114	-0.05325539095166154	1.6901120777902847
111	115	-0.38942577726297756	1.0333886497891367
112	116	-0.5378760718213311	1.439634824350961
113	117	-0.5394697673034108	1.0029399334705835
114	119	-0.9782143951775982	0.03249865801889638
115	120	-0.5530457323505511	1.192862016437666
116	122	-0.6579669576483241	1.1218888140467218
117	123	-0.7793192960747304	1.3339479822876714
118	124	-0.9988268989017546	0.0018986937946008043
119	79	-0.9430808089707724	0.11131677445301608
120	80	-0.8241672394503431	0.3129212129095028
121	126	-0.7012697490949262	0.41132099233530295
122	145	-0.9521841241057868	0.07354926953834551
123	127	-0.889824734195901	0.19770028660786293
124	128	-0.9480534091873971	0.09139796177588501
125	129	-0.9312953358998916	0.11569834819680357
126	130	51.091848708183	106.43047044371573
127	132	-0.2960207064892896	3.337225978461549
128	133	18.43031436092477	52.18846543174015
129	143	-0.8698109654290115	0.22690237283996142
130	144	-0.5021457432345666	0.7048335763741225
131	146	3.469185139494731	9.297425795867582
132	134	1.1759614887805374	3.256689028208205
133	135	-0.9552652606015356	0.09531772765487428
134	140	1.4429820142149303	4.093383104180774
135	141	-0.3195566146362	1.23246106400096
136	152	-0.013902147545258425	1.725746898663087
137	151	-0.12529016597197862	1.9182411316290184
138	149	-0.02659720419677636	1.3843950873645845
139	71	-0.11091938213626273	1.6602470368864604
140	148	-0.04035464532147659	1.8219400837053314
141	150	14.897649479864643	33.30890173009845
142	157	-0.4655394075688859	1.2144534735040442
143	160	-0.026645502845255797	1.6048836320899678
144	64	-0.3696109426932713	2.88601922900399
145	72	-0.2624425735774949	2.3028212689581182
\.


--
-- Data for Name: network_metrics; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.network_metrics (id, project_id, tvl, tvl_fdv) FROM stdin;
1	1	1204213027.497636	0.0798215856906422
4	4	8000000	0.01
8	8	778062650.2429245	0.07416945644523604
9	9	3178096781.653675	0.32991681562724395
10	10	205200000	0.05
12	12	48200000	0.01
13	13	142240000	0.03
15	15	0	0
16	16	5352245.611071278	0.0030412465940098912
17	17	0	\N
18	18	316100000	0.95
19	19	1100000	0.01
21	21	181690000	0.02
22	22	614290000	2.53
23	23	126055534.35682778	0.23079684883411564
26	26	3136000000	1.73
28	28	132050000	3.04
31	31	900290000	0.38
32	32	31150000	0.07
39	39	\N	0
40	40	0	0
41	41	\N	0
42	42	2	0
43	43	164540000	\N
44	44	117110000	0.43
45	45	\N	0
46	46	\N	0
47	47	0	0
49	49	\N	0
50	50	\N	0
51	51	2202694.531564411	0.00397287703624495
52	52	\N	0
53	53	\N	0
54	54	\N	0
55	55	\N	0
56	56	\N	0
57	57	\N	0
58	58	\N	0
60	60	\N	0
65	65	29017.77788235677	7.703751996122767e-05
66	66	\N	0
67	67	\N	\N
68	68	639828.7525947952	0.005977799251442581
69	69	\N	0
70	70	4660000	0.03
73	73	\N	\N
75	75	\N	0
76	76	0	0
77	77	\N	0
78	78	17025	0
84	84	\N	0
85	85	\N	0
86	86	0	0
87	87	\N	0
88	88	\N	0
89	89	\N	0
90	90	\N	0
91	91	0	0
92	92	\N	0
93	93	\N	0
94	94	\N	0
95	95	0	0
96	96	\N	0
97	97	0	0
98	98	0	0
99	152	71910693106.03482	0.16167528674546505
100	151	9128339638.220245	0.06531494458469533
101	149	0	0
102	6	344313090.72154707	0.009738903083938141
103	71	0	0
104	5	0	0
105	140	206310137.0655076	0.2554963460416023
106	29	7971299718.388147	0.44294877430870583
107	7	660281592.0531604	0.01370431198739784
108	20	1457327411.069668	0.07350250779961086
109	27	56839.17407855125	4.051393208524851e-06
110	126	40367291.51538617	0.0024394469051654795
111	144	103852085.17562628	0.014582965669533642
112	146	120020664.19771978	0.04886380688680746
113	114	2265492.3311061678	0.005797484715213069
114	157	7355654.341982685	0.01315926893057359
115	25	329571959.71018595	0.03533120311931276
3	3	1718374885.9239354	0.04150984392682937
2	2	270467566.27113193	0.03794198404416587
\.


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.project (id, coin_name, category) FROM stdin;
1	APT	Layer 1
2	SEI	Layer 1
3	SUI	Layer 1
4	FLR	Layer 1
5	KAS	Layer 1
6	TON	Layer 1 (OLD)
7	ADA	Layer 1 (OLD)
8	OP	Layer 2 (ETH)
9	ARB	Layer 2 (ETH)
10	MNT	Layer 2 (ETH)
12	IMX	Layer 2 (ETH)
13	STRK	Layer 2 (ETH)
14	POL	Layer 2 (ETH)
15	TIA	Layer 1
16	DYM	Modular Blockchain
17	GSWIFT	Modular Blockchain
18	STG	DeFi
19	HFT	DeFi
20	AVAX	Layer 1 (OLD)
21	JUP	DeFi
22	GMX	DeFi
23	OSMO	DeFi
24	ATOM	Layer 1 (OLD)
25	NEAR	Layer 1 (OLD)
26	ETHFI	DeFi
27	DOT	Layer 1 (OLD)
28	QUICK	DeFi
29	TRX	Layer 1 (OLD)
31	JTO	DeFi
32	MAV	DeFi
39	NYM	Infrastructure
40	PYTH	Infrastructure
41	ALT	Infrastructure
42	ZK	Layer 2 (ETH)
43	AXL	Infrastructure
44	ACX	Infrastructure
45	KYVE	Infrastructure
46	CERE	Infrastructure
47	APE	GameFi / Metaverse
49	MEME	GameFi / Metaverse
50	SHRAP	GameFi / Metaverse
51	XAI	GameFi / Metaverse
52	MAGIC	GameFi / Metaverse
53	ACE	GameFi / Metaverse
54	BIGTIME	GameFi / Metaverse
55	AGI	GameFi / Metaverse
56	ZTX	GameFi / Metaverse
57	PIXEL	GameFi / Metaverse
58	MAVIA	GameFi / Metaverse
60	FAR	GameFi / Metaverse
61	MRS	GameFi / Metaverse
62	CATS	TON
63	NOT	TON
64	HMSTR	TON
65	CYBER	SocialFi
66	BBL	SocialFi
67	HOOK	SocialFi
68	RSS3	SocialFi
69	ACS	SocialFi
70	CPOOL	RWA
71	DOGS	TON
72	CATI	TON
73	ALI	AI
75	TAO	AI
76	PAAL	AI
77	NFP	AI
78	0X0	AI
79	AI	AI
80	CGPT	AI
84	ID	Digital Identity
85	ARKM	Digital Identity
86	ENS	Digital Identity
87	GAL	Blockchain Service
88	BICO	Blockchain Service
89	HONEY	Blockchain Service
90	DIMO	Blockchain Service
91	FORT	Blockchain Service
92	WLD	Digital Identity
93	EDU	Blockchain Service
94	TOMI	Digital Identity
95	TOKEN	Blockchain Service
96	WIFI	Blockchain Service
97	CSIX	Blockchain Service
98	NUM	Digital Identity
99	L3	Digital Identity
109	BLUR	NFT Platforms / Marketplaces
110	AGLD	NFT Platforms / Marketplaces
111	WE	NFT Platforms / Marketplaces
112	MYRIA	NFT Platforms / Marketplaces
113	LOOKS	NFT Platforms / Marketplaces
114	OAS	NFT Platforms / Marketplaces
115	ULTIMA	NFT Platforms / Marketplaces
116	MPLX	NFT Platforms / Marketplaces
117	LMWR	NFT Platforms / Marketplaces
118	FLIX	NFT Platforms / Marketplaces
119	GF	NFT Platforms / Marketplaces
120	PANDORA	NFT Platforms / Marketplaces
122	ADF	NFT Platforms / Marketplaces
123	BFIC	Infrastructure
124	SSV	Infrastructure
126	XLM	RWA
127	POLYX	RWA
128	HIFI	RWA
129	RBN	RWA
130	T	Blockchain Service
132	GG	Blockchain Service
133	MOBILE	Blockchain Service
134	BTRST	SocialFi
135	CHEEL	SocialFi
140	DYDX	DeFi
141	NTRN	DeFi
143	ONDO	Financial sector
144	HBAR	Financial sector
145	XRP	Financial sector
146	ALGO	Financial sector
148	BTC	Layer 1 (OLD)
149	ZKJ	Layer 1
150	TAI	Modular Blockchain
151	SOL	Layer 1 (OLD)
152	ETH	Layer 1 (OLD)
153	SOI	Layer 1
154	SIO	Layer 1 (OLD)
155	ИСТОРИЯРАСЧЕТОВ	Layer 1
156	ЫГШ	Layer 1
157	VENOM	Layer 1
158	PDF	Layer 1
159	МУТЩЬ	Layer 1
160	BNB	Layer 2 (ETH)
161	ZRO	Layer 1
\.


--
-- Data for Name: social_metrics; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.social_metrics (id, project_id, twitter, twitterscore) FROM stdin;
1	1	3.85K	1
2	2	769K	220
3	3	867K	309
4	4	307K	99
8	8	715K	682
9	9	1.11M	603
10	10	863K	184
12	12	432K	382
13	13	333K	152
15	15	399K	250
16	16	209K	177
17	17	222K	52
18	18	259722	157
19	19	193633	154
21	21	430K	282
22	22	233170	161
23	23	190K	217
26	26	189K	159
28	28	185485	142
31	31	77.6K	156
32	32	219555	64
39	39	163K	127
40	40	242K	265
41	41	664K	143
42	42	1.5M	524
43	43	\N	\N
44	44	116K	135
45	45	72.1K	54
46	46	6.52K	1
47	47	431K	318
49	49	2.01M	70
50	50	469K	150
51	51	310K	165
52	52	313K	219
53	53	711K	52
54	54	745K	175
55	55	257K	38
56	56	203K	60
57	57	323K	123
58	58	434K	84
60	60	197K	66
65	65	598K	108
66	66	119K	28
67	67	170K	26
68	68	88.7K	53
69	69	97896	56
70	70	56.6K	63
73	73	75.4K	137
75	75	\N	\N
76	76	\N	\N
77	77	\N	\N
78	78	32356	20
84	84	790K	50
85	85	\N	\N
86	86	264K	460
87	87	1.47M	214
88	88	123K	144
89	89	48.7K	95
90	90	25.3K	55
91	91	\N	\N
92	92	436K	255
93	93	295K	55
94	94	133K	21
95	95	63.7K	16
96	96	83.8K	11
97	97	293K	38
98	98	146K	31
99	152	3.56M	1000
100	151	2.9M	812
101	149	966K	85
102	125	223K	41
103	6	2.57M	187
104	126	2.03M	742
105	127	2.53M	178
106	128	1.37M	143
107	129	1.04M	502
108	130	558K	445
109	131	1.87M	433
110	132	\N	\N
111	133	1.61M	220
112	134	73.8K	1
113	135	\N	\N
114	136	2.65M	53
115	137	13.9M	48
116	138	3.72M	19
117	139	3.1M	35
118	140	259K	377
119	141	\N	\N
120	142	22.4K	1
121	120	230K	40
122	143	228K	338
123	144	\N	\N
124	145	\N	\N
125	146	\N	\N
126	147	204K	79
127	148	\N	\N
128	150	50.6K	80
129	153	106K	93
130	154	149K	18
131	155	1.04M	51
132	156	768K	262
133	157	1.21M	35
134	158	20.6K	9
135	159	46.7K	116
136	160	3.61M	329
137	161	685K	209
138	162	38K	73
139	163	7.01K	59
140	164	215K	222
141	165	\N	\N
142	166	356K	157
143	167	\N	\N
144	168	111K	58
145	169	120K	5
146	71	3.66M	23
147	5	232K	44
148	122	\N	\N
149	173	3.49M	1000
150	172	2.88M	813
151	170	254K	389
152	124	214K	14
153	123	957K	80
154	14	2.04M	763
155	7	1.39M	145
156	20	1.09M	513
157	29	1.63M	222
158	27	1.51M	508
159	63	2.68M	55
160	64	13.8M	51
161	72	3.1M	38
162	62	5.69K	1
163	109	259K	404
164	116	91.3K	226
165	115	48.2K	1
166	114	124K	37
167	110	24.6K	7
\.


--
-- Data for Name: tokenomics; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tokenomics (id, project_id, circ_supply, total_supply, capitalization, fdv) FROM stdin;
8	8	1255070491	4294967296	3223450184.348725	11030944653.18199
9	9	4097359817	10000000000	4686825641.281137	11438647935.764479
10	10	3366841707.8368406	6219316794.99	3541861890.0579886	6542618587.3542
12	12	1694765880.3898141	2000000000	3592643556.2700586	4239693042.9632115
13	13	2259283720	10000000000	1643956973.6813436	7276452085.802413
16	16	215311868	1036694120	365512078.2576529	1759885443.5589614
17	17	62621513	1396500000	2916671.3048729002	65043645.26061524
18	18	204338417.4544445	1000000000	55241605.49099651	270343708.1444176
19	19	465444944.2513	1000000000	62348884.858593985	133955445.49073668
21	21	1350000000	10000000000	1464574299.365828	10848698513.82095
22	22	9765997.65924179	9765997.65924179	207742721.16891563	207742721.16891563
23	23	695242723.230617	997798958.425667	380562024.3409976	546175283.5604342
26	26	207550055	1000000000	373550801.53217167	1799810660.287089
28	28	744057.17626895	994486.45601584	32742880.27239243	43763237.5580669
31	31	131097355.3	1000000000	471087757.6151832	3593419230.595136
32	32	429057744.01116383	2000000000	68610184.34478197	319817951.3245041
39	39	804560131.504443	1000000000	96024519.75415774	119350333.17472737
40	40	3624988786.438567	9999988786.438566	1859390517.4790208	5129363266.987729
41	41	2286554196.406704	10000000000	428210322.6266298	1872732005.6509392
42	42	3675000000	21000000000	848120668.7226393	4846403821.272224
43	43	863941161.1159209	1179749594.894857	923028959.7394048	1260436578.715889
44	44	138063734	1000000000	43815528.5287203	317357261.45665663
45	45	720067831.530478	1147041912.530478	13055291.574964408	20796605.487793367
46	46	6939923952	10000000000	12661060.418426428	18243802.82261979
47	47	752651515	1000000000	1452652949.8853014	1930047201.0413764
50	50	695459846.4512365	3000000000	29004626.733306047	125117043.98741199
51	51	795121292.5068666	1359333889.4822602	324307049.63636124	554433100.1108291
52	52	275188528.51861477	347714007	181125644.34690303	228861006.326644
53	53	40674732	146307870	139170611.29571405	500599627.92806756
54	54	1317178069.91005	5000000000	278638995.54273343	1057711944.6035177
55	55	1045324204.750659	3000000000	257924453.15733677	740223325.8882381
56	56	4015011825	10000000000	22117109.556700654	55086038.39965192
57	57	1148124004.66	5000000000	317564088.811565	1382969468.1177182
58	58	38801257	250000000	83742359.22490665	539559576.7999645
60	60	1066410000	5000000000	8084395.983782719	37904726.99891561
65	65	30873083	100000000	116289863.10676248	376670717.03452
66	66	835989673.2704921	1000000000	5228472.241997312	6254230.655198048
67	67	203332251.07573897	500000000	83527495.52349311	205396574.0348295
68	68	674916665	1000000000	72239141.8159749	107034165.19723204
69	69	35615804616.1483	87978427267.87637	51182790.38078658	126432112.07536025
70	70	708723546.7431598	1000000000	176010609.04156372	248348752.98047587
73	73	8189833602.669674	9870903732.81426	76539005.80197628	92249634.69713762
75	75	7380936	7380936	3621756407.899612	3621756407.899612
76	76	819528083.459412	1000000000	121235442.11926664	147933236.90324882
77	77	292859589.0410959	1000000000	56969039.54060379	194526802.85162026
78	78	868563455	1000000000	129450549	149039829.2
84	84	796057180.5383956	1995334959.5383956	349828861.9619839	876853792.9099313
85	85	225100000	1000000000	449921829.2834142	1998764234.9329817
86	86	34137960.22345257	100000000	655499528.3850569	1920148491.8678088
87	87	9435821.72159962	81686490.5342553	16874856.494618516	146086673.31634247
88	88	881260458.5006349	1000000000	245666652.29196382	278767360.91159457
89	89	2935355943.659056	6386410903.351824	187122972.15216345	407120707.8656699
90	90	240772921.16661322	1000000000	37773869.19548955	156885869.94112304
91	91	480734585	1000000000	50998421.601838574	106084361.71039905
92	92	678997323.474048	10000000000	1463229850.30155	21549861828.836445
93	93	339343750.1157	1000000000	172809355.83621624	509245730.25817186
94	94	155815686.672359	562339635.4751778	3947144.519655242	14245265.4014105
95	95	1000019789	10000000000	42036243.036787875	420354111.9803568
96	96	502900359.0125714	1000000000	10282897.41593452	20447186.46875627
97	97	396585067.90544856	939599261.3839558	5318089.026588644	12599749.525991067
98	98	700116242	710179226	35861085.436050445	36376527.74022371
108	108	\N	10000000000	\N	21000000000
118	112	25879230810	50000000000	108586198.94820172	209794100.42249575
119	113	999941673	1000000000	65267933.26550379	65271740.37030437
120	147	517287986.5959966	1122619499.5333848	4880745023.482501	10592203332.746775
121	148	19790568	19790568	1894881307496.6606	1894881307496.6606
122	149	76617517.9816	900000000	114554428.73977835	1345632024.9183762
123	150	543380367	999999988	108383275.95158173	199461153.24218628
125	14	8346794281.690921	10312906621.168447	5938939030.614128	7337873869.239341
126	6	2550010363.1906557	5116718570.773705	17619513210.258987	35354401594.713936
127	7	35085884197.24636	44994868463.33723	42777242148.70097	54858426052.04134
128	20	409353597.50651276	447689897.50651276	21455588155.80156	23464921576.168453
129	24	390934204	390934204	3823128888.7817035	3823128888.7817035
130	25	1217906155	1223573443	9284865370.099245	9328070674.446836
131	27	1525560737.4354184	1525560737.4354184	16298540470.970041	16298540470.970041
132	29	86283351344.12567	86283438989.78612	28936017522.404575	28936046915.286594
133	61	84235303	1000000000	199004256.82426912	2362480453.406443
134	62	675067692800.0621	675067692800.0621	750907.48649787	750907.48649787
135	63	102456957533.5629	102456957533.56	966061809.5342847	966061809.5342574
136	64	64375000000	100000000000	280729804.521756	436085133.2376792
137	71	516750000000	550000000000	394413585.8340916	419791915.25641096
138	72	286216950	1000000000	168254878.61838883	587857842.1661918
139	109	2050643884.9410198	3000000000	875371741.2942871	1280629583.3069003
140	110	77310001	77310001	112541405.6731768	112541405.6731768
141	111	362031240	2500000000	13390214.240161495	92465875.59792835
142	114	2963623102.686533	10000000000	154693867.4892475	521975508.1171322
143	115	32030	100000	149219954.0828788	465875598.135744
144	116	755813146	999983869	275567928.1593213	364592074.6833267
145	117	308742216.61402553	633045269	124610973.16743311	255502431.42727348
146	118	250758585	357242302	36606592.67181154	52151448.511540644
147	119	29300717.91301564	1000000000	259674.2148442173	8862384.04175304
148	120	10000	10000	14467149.821557658	14467149.821557658
149	122	180406874.4019432	1000000000	54201.77047993035	300441.8244017121
150	123	10578424	21000000	18626608.90277019	36977038.06901426
151	124	11562596.23155108	11838486.3	382877366.53218377	392013036.47557133
152	79	239375000	1000000000	110519985.49727604	461702289.2836597
153	80	744164387	998099628	93374433.66385332	125237096.98110382
154	126	29996539741.149803	50001786911.16305	9927133798.24014	16547722940.765486
155	145	56931242174	99987013354	81973162183.89064	143967553648.31015
156	127	909908691.155731	1109003795.327832	296319126.70831966	361156058.12090445
49	49	32708535608.136562	69000000000	548018284.0155785	1156067090.5630062
1	1	535343491.82735777	1129365221.7618222	7438953671.315123	15693280465.600668
2	2	3982916666	10000000000	2839202546.866796	7128450793.619482
4	4	52907111181.716705	102766386590.28001	1740239193.619844	3380227907.6786137
15	15	441857753.311294	1087669479.451755	3722756583.6251225	9163873860.066618
124	5	25296522710.115242	25296522710.115242	4055048668.199843	4055048668.199843
157	128	140393133.17022243	141434815.17022243	80810433.26691455	81410026.50801903
158	129	110041531.39319624	1000000000	39520318.7832241	359140029.0678579
159	99	0	3333333333	0	167746067.61681825
160	130	9996068399.47894	11035000000	270503446.2000683	298617957.533519
161	132	162237935	1000000000	6280525.95593789	38711821.35015396
162	133	89279616082.71985	100882040807.72276	58206263.740393005	65770518.866063155
163	143	1389759838.4783604	10000000000	1353528959.3299668	9739301150.13208
164	144	38198871415.58773	50000000000	5440638807.992581	7121465381.530136
165	146	8280060674.669627	10000000000	2033771916.447989	2456228277.009741
166	134	241347782	250000000	82469270.8907268	85425760.08708338
167	135	56799582.10122949	1000000000	580255565.0643005	10215842152.327038
168	140	643931707.21	770455822.33	811917815.3948859	971448992.3703038
169	141	290681247.477914	999835492.249679	103069480.03504026	354520717.1115601
170	151	475242030.9784796	589414408.0371912	109960667219.22696	136377671484.4696
171	152	120441990.11961582	120441990.11961582	447003194859.8672	447003194859.8672
172	157	988919270	7252848418.426969	76215234.2389294	558971351.7361838
173	160	144009377.3	144009377.3	111181765788.24054	111181765788.24054
3	3	2927660018.558888	10000000000	12119576887.070852	41396804308.70725
\.


--
-- Data for Name: top_and_bottom; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.top_and_bottom (id, project_id, lower_threshold, upper_threshold) FROM stdin;
1	1	5.491	14.87
2	2	0.2515	0.7218
3	3	0.7794	3.943
4	4	0.01312	0.01861
8	8	1.289	2.676
9	9	0.4599	1.143
10	10	0.31	0.95
12	12	1.022	2.25
13	13	0.3174	0.522
15	15	3.724	8.938
16	16	1.13	2.106
17	17	0.04899	0.1087
18	18	0.2569	0.4005
19	19	0.1119	0.2018
21	21	0.6589	1.111
22	22	17.66	36.71
23	23	0.3546	0.6886
26	26	1.199	2.057
28	28	0.02248	0.06172
31	31	1.799	3.728
32	32	0.1157	0.2615
39	39	0.056	0.15
40	40	0.243	0.5532
41	41	0.07121	0.1509
42	42	0.08	0.1579
43	43	0.46	0.9205
44	44	0.03	0.21
45	45	0.01792	0.02945
46	46	0.001796	0.003982
47	47	0.6024	2.122
49	49	0.008916	0.01786
50	50	0.01811	0.0596
51	51	0.1694	0.319
52	52	0.2787	0.5265
53	53	1.805	3.428
54	54	0.06584	0.2415
55	55	0.1057	0.5617
56	56	0.004688	0.008791
57	57	0.1132	0.2904
58	58	1.02	1.894
60	60	0.09641	0.0967
65	65	2.644	4.872
66	66	0.005539	0.02176
67	67	0.3199	0.526
68	68	0.09615	0.1592
69	69	0.001357	0.001998
70	70	0.1129	0.3149
73	73	0.007964	0.01396
75	75	164.03	681.74
76	76	0.1287	0.2979
77	77	0.1686	0.3044
78	78	0.08412	0.2398
84	84	0.3081	0.5281
85	85	0.8922	2.554
86	86	14.56	22.96
87	87	1.567	3.122
88	88	0.1677	0.3112
89	89	0.04861	0.09927
90	90	0.115	0.2275
91	91	0.104	0.1799
92	92	1.317	2.855
93	93	0.4231	0.7369
94	94	0.0223	0.6177
95	95	0.03524	0.07982
96	96	0.0167	0.05315
97	97	0.01223	0.03066
98	98	0.0355	0.07276
99	5	0.1008	0.1923
100	14	0.2854	0.7675
101	6	4.457	7.201
102	7	0.3035	1.327
103	20	20.48	55.01
104	24	3.624	6.192
105	25	3.076	5.878
106	27	3.667	11.65
107	29	0.1465	0.4501
108	61	1.127	1.765
109	63	0.005561	0.01065
110	109	0.1502	0.4417
111	110	0.6524	3.984
112	111	0.0463	0.0875
113	112	0.001505	0.004427
114	113	0.0297	0.05552
115	114	0.02956	0.05277
116	115	4696.9	7949.44
117	116	0.2412	0.7514
118	117	0.1378	0.3001
119	119	0.2727	0.4068
120	120	1212.81	3236.83
121	122	0.0002678	0.0008784
122	123	1.32	7.979
123	124	16.41	26.56
124	79	0.2799	0.5474
125	80	0.09957	0.1772
126	126	0.07575	0.1043
127	145	0.4322	0.6648
128	127	0.1576	0.2828
129	128	0.3409	0.5998
130	129	0.2693	0.4535
131	130	0.01878	0.03837
132	132	0.0116	0.05499
133	133	0.0006091	0.001636
134	143	0.5013	0.8737
135	144	0.0451	0.06385
136	146	0.1058	0.2201
137	134	0.3	0.449
138	135	10.25	21.84
139	140	0.8051	1.349
140	141	0.2877	0.5211
141	152	2150.58	3763.68
142	151	120.62	264.52
143	149	1.08	1.536
144	71	0.0004705	0.0008786
145	148	52552.05	99772.99
146	150	0.09894	0.2073
147	157	0.06346	0.1442
148	160	481.06	793.18
149	64	0.001529	0.007
150	72	0.2659	0.8302
\.


--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public."user" (id, telegram_id, language) FROM stdin;
1	833825243	RU
\.


--
-- Name: funds_profit_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.funds_profit_id_seq', 2, true);


--
-- Name: social_metrics social_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.social_metrics
    ADD CONSTRAINT social_metrics_pkey PRIMARY KEY (id);


--
-- Name: idx_17108_user_pkey; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_17108_user_pkey ON public."user" USING btree (id);


--
-- Name: idx_17113_project_pkey; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_17113_project_pkey ON public.project USING btree (id);


--
-- Name: idx_17118_calculation_pkey; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_17118_calculation_pkey ON public.calculation USING btree (id);


--
-- Name: idx_17123_basic_metrics_pkey; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_17123_basic_metrics_pkey ON public.basic_metrics USING btree (id);


--
-- Name: unique_coin_name; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX unique_coin_name ON public.project USING btree (coin_name);


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: -; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE cryptoanalyst GRANT ALL ON TABLES  TO PUBLIC;


--
-- PostgreSQL database dump complete
--


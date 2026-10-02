# Presentation Script: Chen et al. (2024)
# "Exploring cross-cultural disparities in tourists' perceived images"

---

## SECTION 1: Introduction — What is this paper about?

This paper examines how tourists from different cultural backgrounds
perceive the same destination differently. The authors collected over
100,000 Chinese-language reviews and 16,000 English-language reviews
about Xiamen, China, from multiple online travel platforms.
They used two main NLP techniques: LDA topic modeling to discover
what each group talks about, and a BERT-BILSTM model for sentiment
classification. The theoretical framework is based on Hofstede's
cultural dimensions theory.

---

## SECTION 2: Hofstede's Cultural Dimensions — The theoretical lens

The paper uses three of Hofstede's six cultural dimensions to
explain the differences between Chinese-speaking and English-speaking
tourists:

1. **Collectivism vs. Individualism**: Eastern cultures tend toward
   collectivism (group harmony, family focus), while Western cultures
   lean toward individualism (personal experience, self-expression).

2. **Power Distance**: The degree to which less powerful members of
   a society accept unequal power distribution. Eastern cultures
   generally show higher power distance (respect for hierarchy,
   service expectations).

3. **Uncertainty Avoidance**: How much a culture tolerates ambiguity
   and uncertainty. Higher uncertainty avoidance leads to more
   extensive planning and risk-reducing behaviors.

---

## SECTION 3: The Five Hypotheses

### H1 — Ratings and Collectivism

Chinese-speaking tourists are less inclined to assign low overall
ratings compared to English-speaking tourists.

Why? In collectivist societies, people tend to prioritize harmony
and avoid extreme negative expressions. In individualist societies,
people are more comfortable expressing dissatisfaction directly.
The data confirmed this: Chinese reviews had a 97% favorable rate,
while English reviews had 90.45%.

### H2 — Family Activities and Power Distance

Chinese-speaking tourists devote more time to family-related
activities than English-speaking tourists.

Why? In high power distance cultures like China, family cohesion
is central. Confucian values emphasize collective family time.
In lower power distance Western cultures, individualistic tourists
seek novelty and personal experiences over structured family
activities. The word "children" appeared significantly more in
Chinese reviews.

### H3 — Price Sensitivity

Chinese-speaking tourists pay greater attention to the price of
tourism products than English-speaking tourists.

Why? This connects to collectivist values of frugality and
cost-effectiveness. Chinese tourists showed higher price sensitivity,
focusing on ticket prices and value for money. English-speaking
tourists, often from higher-income backgrounds, prioritized quality
and accommodation over price.

### H4 — Service and Staff Topics

Chinese-speaking tourists generate more topics related to service
and service staff than English-speaking tourists.

Why? In high power distance cultures, there is an expectation of
high-quality service from attendants. Chinese tourists are more
critical of the functional attributes of service. English-speaking
tourists focused more on leisure activities like shopping, nightlife,
and entertainment on pedestrian streets.

### H5 — Travel Planning and Uncertainty Avoidance

Chinese-speaking tourists engage in more extensive travel planning
than English-speaking tourists.

Why? Asian tourists generally demonstrate higher uncertainty avoidance,
meaning they prefer to reduce risk through detailed planning:
using travel agents, pre-arranging itineraries, and pre-purchasing
tour components. Western tourists, with lower uncertainty avoidance,
are more comfortable with spontaneous travel.

---

## SECTION 4: Results Summary

All five hypotheses were statistically confirmed (p < 0.01) using
bootstrap t-tests with 5,000 replications. The key findings:

- Chinese tourists rate more favorably (H1 confirmed)
- Chinese tourists mention family activities more (H2 confirmed)
- Chinese tourists are more price-sensitive (H3 confirmed)
- Chinese tourists discuss service quality more (H4 confirmed)
- Chinese tourists plan travel more extensively (H5 confirmed)

---

## SECTION 5: Why this matters for our research

This paper is a direct antecedent to our study. The similarities:
- Both compare domestic vs. foreign tourist perceptions
- Both use LDA topic modeling
- Both use sentiment analysis (they use BERT-BILSTM, we use
  pre-trained classifiers per language)
- Both frame findings through cultural theory

The differences:
- They study Xiamen (China), we study Seoul and Busan (Korea)
- They compare Chinese vs. English speakers
- We compare Korean vs. English speakers
- We add cross-lingual embeddings, ABSA, and motivation classification
- We collect from culturally segmented platforms per location,
  not aggregated across many platforms

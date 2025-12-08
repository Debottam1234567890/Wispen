# Flashcard Set: Learning Material

*Generated: 2025-12-04T20:21:24.957388*
*Total Cards: 10*


## Easy Cards (5)

### Card 1 [DEFINITION]

**Front:** Machine Learning

**Back:** A type of AI that lets computers learn from data without being specifically told what to do.

**Explanation:** Machine learning algorithms improve automatically through experience. For example, a program can learn to identify cats in pictures by being shown many pictures of cats.

**Tags:** AI, Algorithms, Learning, Data

---

### Card 2 [DEFINITION]

**Front:** Artificial Intelligence

**Back:** Broad field of computer science focused on creating intelligent agents.

**Explanation:** Artificial intelligence aims to make computers think and act like humans. This involves developing algorithms and systems that can solve problems, learn, and make decisions.

**Tags:** AI, Computer Science, Intelligence

---

### Card 3 [DEFINITION]

**Front:** What type of machine learning uses labeled data to learn?

**Back:** Supervised Learning

**Explanation:** Supervised learning is like learning with a teacher. The 'labeled' data acts as the teacher, showing the algorithm what the correct answer is for each example, allowing it to learn and make predictions on new data.

**Tags:** machine learning, supervised learning, labeled data

---

### Card 4 [DEFINITION]

**Front:** Unsupervised Learning

**Back:** Finding patterns in data without labels.

**Explanation:** Unsupervised learning algorithms explore data on their own to discover hidden structures. Unlike supervised learning, there are no 'right' answers provided during training, so the algorithm must learn to identify patterns without guidance. For example, grouping customers based on their purchasing behavior.

**Tags:** Machine Learning, Unsupervised, Patterns, Data

---

### Card 5 [DEFINITION]

**Front:** Training Data

**Back:** A dataset used to teach a model how to make predictions.

**Explanation:** Training data is like the textbook a student uses to learn. The model learns patterns from this data, enabling it to make predictions on new, unseen data. Without training data, a model would have no basis for making informed decisions.

**Tags:** data, model, machine learning

---


## Medium Cards (4)

### Card 1 [DEFINITION]

**Front:** Reinforcement Learning

**Back:** A type of machine learning where an agent learns to make decisions by interacting with an environment to maximize a cumulative reward. The agent learns through trial and error, receiving feedback in the form of rewards or penalties for its actions.

**Explanation:** Reinforcement learning (RL) differs from supervised learning because it doesn't require labeled data. Instead, an agent explores the environment and learns which actions lead to the most reward over time. Think of a dog learning tricks - it gets treats (rewards) for performing the trick correctly.

**Tags:** Machine Learning, Agent, Reward, Policy

---

### Card 2 [DEFINITION]

**Front:** Overfitting

**Back:** A model performs well on the training data but poorly on new, unseen data.

**Explanation:** Overfitting occurs when a model learns the training data too well, including its noise and specific patterns. This leads to high accuracy on the training set but poor generalization to new data. Regularization techniques are often used to prevent overfitting.

**Tags:** Overfitting, Machine Learning, Generalization, Model Complexity

---

### Card 3 [DEFINITION]

**Front:** What is Linear Regression?

**Back:** A supervised learning algorithm that models the relationship between a dependent variable and one or more independent variables by fitting a linear equation to observed data. It's used for predicting continuous numerical values.

**Explanation:** Linear Regression aims to find the best-fitting line (or hyperplane in higher dimensions) that minimizes the difference between predicted and actual values. This allows for making predictions about future data points based on the learned linear relationship. It is a supervised learning algorithm because it learns from labeled data (input features and corresponding target values).

**Tags:** Regression, Supervised Learning, Prediction, Linear Model

---

### Card 4 [DEFINITION]

**Front:** What type of algorithm is Logistic Regression used for?

**Back:** Binary classification.

**Explanation:** Logistic Regression is specifically designed to predict the probability of a binary outcome (0 or 1, yes or no). It uses a sigmoid function to map predicted values between 0 and 1, making it suitable for classification tasks where you need to assign data points to one of two categories.

**Tags:** Classification, Supervised Learning, Binary Classification, Sigmoid Function

---


## Hard Cards (1)

### Card 1 [DEFINITION]

**Front:** Explain the vanishing gradient problem in deep neural networks and describe a strategy to mitigate it.

**Back:** The vanishing gradient problem occurs when gradients become extremely small during backpropagation, preventing weights in earlier layers from updating effectively. This is often caused by activation functions with gradients that saturate at 0 (e.g., sigmoid, tanh). Mitigation strategies include using ReLU or Leaky ReLU activation functions (which don't saturate as easily), batch normalization (which normalizes activations), and skip connections (e.g., in ResNets) that allow gradients to bypass layers.

**Explanation:** The vanishing gradient problem is a significant obstacle in training deep networks. Understanding its cause and the effectiveness of different mitigation strategies is crucial for building successful deep learning models. ReLU and skip connections directly address the issue of diminishing gradients, while batch normalization helps stabilize training and allows for higher learning rates.

**Tags:** vanishing gradient, backpropagation, ReLU, deep learning

---


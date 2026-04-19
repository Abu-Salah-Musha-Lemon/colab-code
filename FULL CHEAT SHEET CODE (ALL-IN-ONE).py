# ==============================
# 1. IMPORT LIBRARIES
# ==============================
 import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# ==============================
# 2. LOAD DATA
# ==============================
url = "https://raw.githubusercontent.com/rashakil-ds/Linear-Regression-with-Python/refs/heads/main/Salary%20Data.csv"
df = pd.read_csv(url)

# ==============================
# 3. SPLIT DATA
# ==============================
X = df[['YearsExperience']]
y = df['Salary']

# ==============================
# 4. TRAIN MODEL
# ==============================
model = LinearRegression()
model.fit(X, y)

# ==============================
# 5. PREDICTIONS
# ==============================
y_pred = model.predict(X)

df['Predicted Salary'] = y_pred

# ==============================
# 6. ERROR CALCULATIONS
# ==============================
df['Error'] = df['Salary'] - df['Predicted Salary']
df['Abs Error'] = abs(df['Error'])
df['Squared Error'] = df['Error'] ** 2

# ==============================
# 7. MODEL PARAMETERS
# ==============================
m = model.coef_[0]
c = model.intercept_

print("\n===== MODEL EQUATION =====")
print(f"Salary = {m:.2f} * Experience + {c:.2f}")

# ==============================
# 8. PERFORMANCE METRICS
# ==============================
mse = mean_squared_error(y, y_pred)
mae = mean_absolute_error(y, y_pred)
rmse = np.sqrt(mse)
r2 = r2_score(y, y_pred)

print("\n===== PERFORMANCE METRICS =====")
print("MSE  :", mse)
print("MAE  :", mae)
print("RMSE :", rmse)
print("R²   :", r2)

# ==============================
# 9. SUMMARY TABLE
# ==============================
print("\n===== DATA WITH PREDICTIONS =====")
print(df.head())

# ==============================
# 10. VISUALIZATION
# ==============================
plt.figure(figsize=(8,5))

# actual data
plt.scatter(X, y, color='blue', label='Actual Data')

# regression line
plt.plot(X, y_pred, color='red', label='Regression Line')

# error lines
for i in range(len(X)):
    plt.plot([X.iloc[i], X.iloc[i]],
             [y.iloc[i], y_pred[i]],
             color='green', alpha=0.4)

plt.xlabel("Years of Experience")
plt.ylabel("Salary")
plt.title("Salary Prediction using Linear Regression")
plt.legend()
plt.show()

# ==============================
# 11. RESIDUALS (OPTIONAL ANALYSIS)
# ==============================
residuals = y - y_pred

plt.figure(figsize=(6,4))
plt.scatter(y_pred, residuals, color='purple')
plt.axhline(y=0, color='black', linestyle='--')
plt.xlabel("Predicted Salary")
plt.ylabel("Residuals")
plt.title("Residual Plot")
plt.show()

# ==============================
# 12. PREDICT NEW VALUE
# ==============================
new_exp = [[5]]
pred_salary = model.predict(new_exp)

print("\nPrediction for 5 years experience:", pred_salary[0])

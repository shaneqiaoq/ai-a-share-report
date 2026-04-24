import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import numpy as np

df = pd.read_csv('biomed_data.csv', index_col=0)
df_t = df.T 

plt.figure(figsize=(12, 7))

for city in df_t.columns:
    # Prepare historical data
    years = df_t.index.astype(int).values.reshape(-1, 1)
    values = df_t[city].values

    plt.plot(years, values, marker='o', label=f'{city} (History)')

    model = LinearRegression()
    model.fit(years, values)

    future_years = np.array([2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034]).reshape(-1, 1)
    future_values = model.predict(future_years)

    plt.plot(future_years, future_values, linestyle='--', alpha=0.7, label=f'{city} (Prediction)')

plt.title('Biomed Patent Trends & 10-Year Prediction', fontsize=15)
plt.xlabel('Year', fontsize=12)
plt.ylabel('Patent Count', fontsize=12)
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()

plt.savefig('prediction_result.png')
print("✅ Prediction complete! Image saved as prediction_result.png")

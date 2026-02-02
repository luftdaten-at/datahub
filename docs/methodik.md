# City Current
Berechnen der Mittelwerte der letzten Stunde (1h-Mittelwerte)
## Filtering
Beim Filtering werden die Daten nach Dimension gruppiert, dort werden nur Werte betrachtet die in den letzten 60 minuten gemessen wurden.

Um die Datenqualität zu verbessern werden die kleinsten 5% und größten 5% aller Werte verworfen. Aus den übrigen 90% der Daten wird ein Mittelwert mittels dem Arithmetischen mittel berechnet.

```python
ALPHA = 0.1
l = np.percentile(a, 100 * (ALPHA / 2))
r = np.percentile(a, 100 * (1 - (ALPHA / 2)))

```
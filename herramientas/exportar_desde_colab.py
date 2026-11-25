# =====================================================================
# Ejecutar en Google Colab (una sola vez). NO es parte de la app web.
#
# Hace dos cosas:
#   1. Exporta a CSV las tablas LMS de la OMS que traen anthro y anthroplus.
#   2. Genera casos de prueba calculados con R, para validar la versión en Python.
# Al final descarga un archivo "datos_oms.zip".
# =====================================================================

import os

print("Instalando paquetes de R (puede tardar un par de minutos)...")
os.system("Rscript -e 'if(!require(anthro)) install.packages(\"anthro\", repos=\"https://cloud.r-project.org\", quiet=TRUE)' > /dev/null 2>&1")
os.system("Rscript -e 'if(!require(anthroplus)) install.packages(\"anthroplus\", repos=\"https://cloud.r-project.org\", quiet=TRUE)' > /dev/null 2>&1")

import rpy2.robjects as robjects

codigo_r = r'''
library(anthro)
library(anthroplus)

dir.create("datos_oms", showWarnings = FALSE)

# ---------- 1. Tablas LMS de la OMS ----------
wfl <- anthro:::growthstandards_wflanthro    # Peso para la longitud (0 a 2 años)
wfh <- anthro:::growthstandards_wfhanthro    # Peso para la talla (2 a 5 años)
len <- anthro:::growthstandards_lenanthro    # Talla para la edad (0 a 5 años)
bfa <- anthroplus:::bfa_growth_standards     # IMC para la edad (5 a 19 años)
hfa <- anthroplus:::hfa_growth_standards     # Talla para la edad (5 a 19 años)

write.csv(wfl, "datos_oms/wfl.csv", row.names = FALSE)
write.csv(wfh, "datos_oms/wfh.csv", row.names = FALSE)
write.csv(len, "datos_oms/len.csv", row.names = FALSE)
write.csv(bfa, "datos_oms/bfa.csv", row.names = FALSE)
write.csv(hfa, "datos_oms/hfa.csv", row.names = FALSE)

# ---------- 2. Casos de prueba ----------
set.seed(42)
n <- 400
sex <- sample(1:2, n, replace = TRUE)
age_days <- sample(0:(19 * 365), n, replace = TRUE)
age_months <- age_days / 30.4375

# Talla realista: mediana de la OMS para esa edad, con variación aleatoria
talla_mediana <- sapply(seq_len(n), function(i) {
  if (age_months[i] < 60) {
    len$m[len$sex == sex[i] & len$age == age_days[i]]
  } else {
    hfa$m[hfa$sex == sex[i] & hfa$age == max(61, min(228, round(age_months[i])))]
  }
})
height <- round(talla_mediana * (1 + 0.045 * rnorm(n, sd = 1.5)), 1)

# Peso a partir de un IMC realista (con algunos casos extremos)
imc <- 16.5 * exp(rnorm(n, sd = 0.18))
weight <- round(imc * (height / 100)^2, 1)

casos <- data.frame(sex, age_days, age_months, weight, height)

# Agregar el caso de ejemplo del formulario original
casos <- rbind(casos, data.frame(sex = 1, age_days = 6512, age_months = 6512 / 30.4375,
                                 weight = 64.4, height = 170.5))

menores <- casos[casos$age_months < 60, ]
mayores <- casos[casos$age_months >= 60, ]

r_menores <- anthro_zscores(sex = menores$sex, age = menores$age_days,
                            weight = menores$weight, lenhei = menores$height)
r_mayores <- anthroplus_zscores(sex = mayores$sex, age_in_months = mayores$age_months,
                                weight = mayores$weight, height = mayores$height)

write.csv(cbind(menores, r_menores[, c("cbmi", "zwfl", "zlen")]),
          "datos_oms/prueba_menores_5.csv", row.names = FALSE)
write.csv(cbind(mayores, r_mayores[, c("cbmi", "zbfa", "zhfa")]),
          "datos_oms/prueba_mayores_5.csv", row.names = FALSE)

cat("Menores de 5:", nrow(menores), " | Mayores de 5:", nrow(mayores), "\n")
'''

robjects.r(codigo_r)

os.system("zip -r datos_oms.zip datos_oms > /dev/null")
from google.colab import files
files.download("datos_oms.zip")
print("¡Listo! Se descargó datos_oms.zip")

from gurobipy import *

m = Model("CarritoFonda")

volumen_cooler = 20
volumen_estante = 50
# vol_ocupa_vaso = 0.03
# vol_ocupa_bombilla = 0.01
precio_venta_terremoto = 2500
arriendo_semana = 1750000
sueldo = 300000
M = 99999999999999999999999999999999999999999999999

materiales, cant_receta, volumen_ocupa = multidict({
    "granadina": [0.05, 1],
    "helado": [0.15, 1],
    "pipeno": [0.25, 1],
    "bombilla": [1, 0.01],
    "vaso": [1, 0.03]
})

proveedores_datos = dict({
    'Proveedor1': {
        "costo_viaje": 4432,
        "costo_material": {
            "vaso": 50,
            "bombilla": 7,
            "pipeno": 2560,
            "granadina": 1660,
            "helado": 2460
        }
    },

    'Proveedor2': {
        "costo_viaje": 746,
        "costo_material": {
            "vaso": 48,
            "bombilla": 6,
            "pipeno": 3500,
            "granadina": 3200,
            "helado": 3400
        }
    },

    'Proveedor3': {
        "costo_viaje": 4400,
        "costo_material": {
            "vaso": 47,
            "bombilla": 7,
            "pipeno": 1500,
            "granadina": 1400,
            "helado": 1350
        }
    }
})

proveedores = proveedores_datos.keys()

dias, demanda = multidict({
    "Día1": 160,
    "Día2": 155,
    "Día3": 145,
    "Día4": 155,
    "Día5": 165,
    "Día6": 170,
    "Día7": 170
})

# CREATE VARIABLES:

# x_t_i
restos = {}
for t in dias:
    dic = {}
    for i in materiales:
        dic[i] = m.addVar(
            vtype=GRB.CONTINUOUS, name=("x_" + str(i) + "_" + str(t)))
    restos[t] = dic

# w_t
vasos_vendidos = {}
for t in dias:
    vasos_vendidos[t] = m.addVar(vtype=GRB.INTEGER, name=("w_" + str(t)))

# y_t_i_j
compro_proveedor = {}
for t in dias:
    dic = {}
    for i in materiales:
        dic_proveedores = {}
        for j in proveedores:
            dic_proveedores[j] = m.addVar(
                vtype=GRB.CONTINUOUS, name=(
                    "Y_" + str(t) + "_" + str(i) + "_" + str(j)))
        dic[i] = dic_proveedores
    compro_proveedor[t] = dic

# delta_t_j
deltas = {}
for t in dias:
    dic = {}
    for j in proveedores:
        dic[j] = m.addVar(
            vtype=GRB.BINARY, name=("delta_" + str(j) + "_" + str(t)))
    deltas[t] = dic

m.update()

print(proveedores)


# SET OBJECTIVE FUNCTION:
m.setObjective(
    quicksum(
        vasos_vendidos[t] *
        precio_venta_terremoto for t in dias) -
    sueldo - arriendo_semana -
    quicksum(
        deltas[t][j] *
        compro_proveedor[t][i][j] *
        proveedores_datos[j]["costo_material"][i] for j in proveedores
        for i in materiales
        for t in dias) -
    quicksum(
        deltas[t][j] *
        proveedores_datos[j]["costo_viaje"]
        for j in proveedores
        for t in dias),
    GRB.MAXIMIZE)


# ADD CONSTRAINTS:


for i in materiales:
    for indi in range(len(dias)):
        t = dias[indi]

# R2: Del día anterior al primero no quedaron restos.
# (Esta línea es como la restricción)
        if indi - 1 < 0:
            resto_anterior = 0
        else:
            tanterior = dias[indi - 1]
            resto_anterior = restos[tanterior][i]

# R3: Lo que queda es realmente lo que queda:
# (Definición x_i_t)
        m.addConstr(
            restos[t][i] == (
                resto_anterior +
                quicksum(
                    compro_proveedor[t][i][j] for j in proveedores) -
                vasos_vendidos[t] *
                cant_receta[i]),
            ("R3" + i + t))

# R5: No se venden más vasos que materiales hayan/
# máximo de vasos que puedo preparar con material i
# Del material que haya menos, le va a hacer una cota a las ventas:
for t in dias:
    for i in materiales:
        m.addConstr(vasos_vendidos[t] <= (1 / cant_receta[i]) *
                    (restos[tanterior][i] +
                        quicksum(
                            compro_proveedor[t][i][j] for j in proveedores)),
                    ("R5" + t + i))

# R1: No se supera el volumen del cooler:
        if i == "helado":
            m.addConstr(
                (resto_anterior +
                 quicksum(
                    compro_proveedor[t][i][j] for j in proveedores)) <= volumen_cooler, ("R1" + t))

# R4: No se supera el volumen del estante:
        else:
            m.addConstr(
                volumen_ocupa[i] * (
                    resto_anterior +
                    quicksum(
                        compro_proveedor[t][i][j] for j in proveedores)) <= volumen_estante, ("R1" + t))

# R6: Que no se vendan más vasos que la demanada
for t in dias:
    m.addConstr(vasos_vendidos[t] <= demanda[t], ("R6" + t))

# (R7 && R8: Que se le compre a máximo un proveedor por día)
# R7:
for t in dias:
    for j in proveedores:
        m.addConstr(
            quicksum(
                compro_proveedor[t][i][j] for i in materiales) <= M * deltas[t][j], ("R8" + t + j))
# R8:
for t in dias:
    m.addConstr((quicksum(deltas[t][j] for j in proveedores) <= 1), ("R8" + t))

# R9: Naturaleza de las varibles:
for t in dias:
    for i in materiales:
        #
        m.addConstr(restos[t][i] >= 0, ("R9restos" + t + i))
        for j in proveedores:
            #
            m.addConstr(compro_proveedor[t][i][j] >= 0,
                        ("R9compras" + t + i + j))
    #
    m.addConstr(vasos_vendidos[t] >= 0, ("R9ventas" + t))


# # Solve and print solution
m.optimize()
m.printAttr("X")
print(m.ObjVal)


DROP TRIGGER IF EXISTS sincronizar_estoque_saldo ON {saldo};
DROP TRIGGER IF EXISTS guardar_estoque_derivado ON {produto};
DROP TRIGGER IF EXISTS guardar_estoque_derivado ON {variacao};
DROP FUNCTION IF EXISTS sincronizar_estoque_saldo();
DROP FUNCTION IF EXISTS guardar_estoque_derivado();

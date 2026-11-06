from cyber import indice


def v(chave, categoria, severidade):
    return {"chave": [chave], "rotulo": chave, "categoria": categoria, "severidade": severidade}


def test_sem_vazamento_da_zero_baixo():
    r = indice.calcular([])
    assert r["indice"] == 0 and r["faixa"] == "baixo"


def test_valores_da_tabela_do_readme():
    assert indice.calcular([v("cpf", "identificação", 5)])["indice"] == 22
    um_de_saude = indice.calcular([v("dep", "saúde", 4)])
    assert um_de_saude["indice"] == 33 and um_de_saude["faixa"] == "médio"
    exemplo = indice.calcular([v("tel", "contato", 4), v("dep", "saúde", 4), v("cpf", "identificação", 5),
                               v("end", "localização", 4)])
    assert exemplo["soma"] == 21 and exemplo["indice"] == 65 and exemplo["faixa"] == "alto"


def test_mesmo_defeito_conta_uma_vez():
    r = indice.calcular([v("cpf", "identificação", 5), v("cpf", "identificação", 5)])
    assert r["soma"] == 5


def test_nunca_passa_de_100():
    r = indice.calcular([v(str(i), "saúde", 5) for i in range(50)])
    assert r["indice"] == 100

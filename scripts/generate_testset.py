#!/usr/bin/env python3
"""Generate a use-case evaluation test set: 5 correct + 5 incorrect documents.

Each INCORRECT document is a twin of a CORRECT one with exactly ONE injected
defect, so the expected verdict (and the check that should fail) is unambiguous.
The 5 defects are applied in sequence, one per document.

Output: ./testset/*.md  +  ./testset/manifest.json

Run:  python scripts/generate_testset.py
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# 5 base CORRECT use-case documents (different domains). Each is well-formed:
# actor + goal + testable requirement + main flow + a valid PlantUML use-case
# diagram. All three checks (has_requirement, has_use_case_context,
# symbology_correct) should pass.
# ──────────────────────────────────────────────────────────────────────────────
BASE_DOCS = [
    {
        "key": "login",
        "title": "Realizar Login",
        "actor": "Usuario cadastrado",
        "alias": "Usuario",
        "goal": "Autenticar-se no sistema para acessar funcionalidades restritas.",
        "requirement": (
            "O usuario deve poder realizar login informando e-mail e senha validos; "
            "o sistema valida as credenciais e concede acesso, ou exibe uma mensagem "
            "de erro em caso de falha."
        ),
        "flow": [
            "O usuario acessa a tela de login.",
            "Informa e-mail e senha.",
            "O sistema valida as credenciais.",
            "O sistema concede acesso ao painel.",
        ],
        "system": "Sistema de Autenticacao",
        "ucs": [("Realizar Login", "UC1"), ("Recuperar Senha", "UC2")],
    },
    {
        "key": "carrinho",
        "title": "Adicionar Produto ao Carrinho",
        "actor": "Cliente",
        "alias": "Cliente",
        "goal": "Selecionar produtos para compra e acumula-los no carrinho.",
        "requirement": (
            "O cliente deve poder adicionar um produto ao carrinho informando a "
            "quantidade desejada; o sistema atualiza o subtotal e o total do carrinho."
        ),
        "flow": [
            "O cliente navega no catalogo de produtos.",
            "Seleciona um produto e a quantidade.",
            "O sistema adiciona o item ao carrinho.",
            "O sistema recalcula o total.",
        ],
        "system": "Loja Virtual",
        "ucs": [("Adicionar ao Carrinho", "UC1"), ("Remover do Carrinho", "UC2")],
    },
    {
        "key": "busca",
        "title": "Buscar Produtos",
        "actor": "Visitante",
        "alias": "Visitante",
        "goal": "Encontrar produtos a partir de criterios de busca.",
        "requirement": (
            "O visitante deve poder buscar produtos por palavra-chave e categoria; "
            "o sistema retorna a lista de produtos correspondentes, ordenada por relevancia."
        ),
        "flow": [
            "O visitante informa a palavra-chave e a categoria.",
            "O sistema executa a busca.",
            "O sistema exibe os resultados encontrados.",
        ],
        "system": "Catalogo de Produtos",
        "ucs": [("Buscar Produtos", "UC1"), ("Filtrar Resultados", "UC2")],
    },
    {
        "key": "checkout",
        "title": "Finalizar Pedido",
        "actor": "Cliente",
        "alias": "Cliente",
        "goal": "Concluir a compra dos itens do carrinho.",
        "requirement": (
            "O cliente deve poder finalizar o pedido informando o endereco de entrega "
            "e a forma de pagamento; o sistema confirma o pedido e gera o numero do pedido."
        ),
        "flow": [
            "O cliente revisa os itens do carrinho.",
            "Informa endereco e pagamento.",
            "O sistema processa o pagamento.",
            "O sistema confirma o pedido.",
        ],
        "system": "Checkout",
        "ucs": [("Finalizar Pedido", "UC1"), ("Cancelar Pedido", "UC2")],
    },
    {
        "key": "perfil",
        "title": "Editar Perfil",
        "actor": "Usuario",
        "alias": "Usuario",
        "goal": "Atualizar os dados pessoais da conta.",
        "requirement": (
            "O usuario deve poder editar seu perfil alterando nome e telefone; "
            "o sistema valida os campos e persiste as alteracoes."
        ),
        "flow": [
            "O usuario abre a tela de perfil.",
            "Altera nome e telefone.",
            "O sistema valida os campos.",
            "O sistema salva as alteracoes.",
        ],
        "system": "Gestao de Conta",
        "ucs": [("Editar Perfil", "UC1"), ("Alterar Senha", "UC2")],
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# 5 defect transforms (applied in sequence, one per incorrect document).
# Each breaks exactly one check.
# ──────────────────────────────────────────────────────────────────────────────
def defect_no_requirement(d: dict) -> dict:
    """Replace the testable requirement with vague marketing text."""
    d["requirement"] = (
        "Sistema moderno, intuitivo e facil de usar, com uma excelente experiencia "
        "para o usuario."
    )
    return d


def defect_no_context(d: dict) -> dict:
    """Remove the textual scenario (actor/objetivo/fluxo) -> 'loose diagram'.

    The diagram stays valid, but the document no longer describes a use-case
    context (actor + flow + goal) in prose, so has_use_case_context fails.
    """
    d["omit_context"] = True
    return d


def defect_syntax(d: dict) -> dict:
    """Break PlantUML syntax with an UNCLOSED STRING in the actor declaration.

    We keep @startuml/@enduml so the block is still extractable by the agent's
    regex, but the missing closing quote makes PlantUML reject it.
    """
    p = render_puml(d)
    p = re.sub(r'(actor\s+)"([^"]+)"(\s+as)', r'\1"\2\3', p)
    d["puml_override"] = p
    return d


def defect_class_notation(d: dict) -> dict:
    """Valid PlantUML, but CLASS-diagram notation instead of use-case notation."""
    d["puml_override"] = """@startuml
class Usuario {
  +id: int
  +nome: String
  +email: String
}
class Pedido {
  +id: int
  +total: Decimal
}
Usuario "1" --> "*" Pedido : realiza
@enduml"""
    return d


def defect_sequence_notation(d: dict) -> dict:
    """Valid PlantUML, but SEQUENCE-diagram notation instead of use-case notation."""
    d["puml_override"] = """@startuml
actor Usuario
participant "Sistema" as S
participant "Banco de Dados" as BD
Usuario -> S : solicitar operacao
S -> BD : consultar dados
BD --> S : retorno
S --> Usuario : resultado
@enduml"""
    return d


DEFECTS = [
    ("sem_requisito", "has_requirement", defect_no_requirement),
    ("sem_contexto", "has_use_case_context", defect_no_context),
    ("sintaxe_invalida", "symbology_correct", defect_syntax),
    ("notacao_classe", "symbology_correct", defect_class_notation),
    ("notacao_sequencia", "symbology_correct", defect_sequence_notation),
]


# ──────────────────────────────────────────────────────────────────────────────
# Rendering
# ──────────────────────────────────────────────────────────────────────────────
def render_puml(d: dict) -> str:
    if d.get("puml_override"):
        return d["puml_override"]
    alias = d["alias"]
    lines = ["@startuml", "left to right direction", f'actor "{d["actor"]}" as {alias}']
    lines.append(f'rectangle "{d["system"]}" {{')
    for label, uid in d["ucs"]:
        lines.append(f'  usecase "{label}" as {uid}')
    lines.append("}")
    for _label, uid in d["ucs"]:
        lines.append(f"{alias} --> {uid}")
    if len(d["ucs"]) >= 2:
        lines.append(f'{d["ucs"][0][1]} ..> {d["ucs"][1][1]} : <<extend>>')
    lines.append("@enduml")
    return "\n".join(lines)


def render_md(d: dict) -> str:
    parts = [f"# Caso de Uso: {d['title']}"]
    if not d.get("omit_context"):
        parts += ["", f"Ator principal: {d['actor']}", f"Objetivo: {d['goal']}", "", "Fluxo principal:"]
        parts += [f"{i}. {s}" for i, s in enumerate(d["flow"], 1)]
    parts += ["", "Requisito: " + d["requirement"], "", render_puml(d)]
    return "\n".join(parts) + "\n"


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "testset"
    out.mkdir(exist_ok=True)
    manifest = []

    # 5 correct documents
    for i, d in enumerate(BASE_DOCS, 1):
        fname = f"correto_{i}_{d['key']}.md"
        (out / fname).write_text(render_md(d), encoding="utf-8")
        manifest.append(
            {"file": fname, "name": f"{d['title']} (correto)", "expected_verdict": "correct", "expected_fail": None}
        )

    # 5 incorrect documents: BASE_DOCS[i] + DEFECTS[i] (errors in sequence)
    for i, (slug, check, fn) in enumerate(DEFECTS):
        d = fn(copy.deepcopy(BASE_DOCS[i]))
        fname = f"incorreto_{i + 1}_{slug}.md"
        (out / fname).write_text(render_md(d), encoding="utf-8")
        manifest.append(
            {
                "file": fname,
                "name": f"{BASE_DOCS[i]['title']} -- {slug.replace('_', ' ')}",
                "expected_verdict": "incorrect",
                "expected_fail": check,
            }
        )

    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Console summary
    print(f"Gerado em: {out}\n")
    print(f"{'#':<3} {'documento':<42} {'esperado':<11} {'falha esperada'}")
    print("-" * 80)
    for i, m in enumerate(manifest, 1):
        print(f"{i:<3} {m['file']:<42} {m['expected_verdict']:<11} {m['expected_fail'] or '-'}")
    print(f"\n{len(manifest)} documentos (+ manifest.json). Importe-os na aba "
          "Qualidade > Casos de Uso (botao 'importar .txt/.md') e marque o veredito esperado.")


if __name__ == "__main__":
    main()

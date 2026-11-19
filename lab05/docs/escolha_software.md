# Escolha do software: Moodle

**Issue:** #162 · **Responsável:** Gabriel Assis de Souza · **Data de acesso das evidências:** 19/11/2026

## Software escolhido

**Moodle** é um sistema de gerenciamento de aprendizagem (LMS) de código aberto, mantido pela Moodle HQ. O estudo é sobre o software em operação, não sobre um repositório do GitHub.

## Critério 1: é real

| Evidência | Link | Acesso |
|---|---|---|
| Site oficial do produto | https://moodle.com | 19/11/2026 |
| Comunidade e documentação oficial | https://moodle.org · https://docs.moodle.org | 19/11/2026 |
| Estudo de caso: Nepal Open University usa o Moodle como LMS oficial de todos os programas acadêmicos | https://moodle.com/wp-content/uploads/2019/12/NepalOpenUniversity_Casestudy.pdf | 19/11/2026 |

## Critério 2: está em operação

| Evidência | Link | Acesso |
|---|---|---|
| Versão atual: Moodle 5.3.1 (12/11/2026), da linha 5.3 LTS lançada em 05/10/2026 | https://endoflife.date/moodle | 19/11/2026 |
| Suporte de segurança da 5.3 LTS até 01/10/2029; 5.2, 4.5 LTS e 5.1 também têm releases de 12/11/2026 | https://endoflife.date/moodle | 19/11/2026 |
| Em 22/10/2026 a Moodle HQ comunicou ter tirado sites públicos do ar por precaução contra a vulnerabilidade PHP2SHELL (divulgada em 21/10/2026) e restaurado conforme os patches foram validados | https://moodle.org/news (resumo via busca; a página retornou HTTP 403 ao acesso automático, **confirmar manualmente no navegador**) | 19/11/2026 |
| Empresas ou órgãos que usam: Nepal Open University (acima). A Open University (UK) adotou o Moodle, segundo estudo de 2009 (dado antigo). | https://www.linux-magazine.com/Online/News/Simply-the-Best-Case-Study-for-Moodle-at-Open-University | 19/11/2026 |

## Critério 3: tem alto impacto

| Evidência | Link | Acesso |
|---|---|---|
| Mais de 500 milhões de usuários em sites registrados (comunicado de 03/12/2025) | https://moodle.com/news/500-million-users-on-registered-moodle-sites/ | 19/11/2026 |
| Estatísticas de sites registrados: 147.888 sites, 513.581.641 usuários, 59.374.088 cursos, 237 países (a página não informa a data da estatística) | https://stats.moodle.org | 19/11/2026 |

## Ressalvas

- Os números contam **somente sites registrados**. A própria documentação do Moodle diz que não há como saber o total real (https://docs.moodle.org/503/en/Usage).
- O incidente PHP2SHELL deve ser descrito com cuidado: é uma vulnerabilidade do PHP, e a fonte primária (moodle.org/news) precisa ser lida diretamente antes de entrar no relatório.
- As evidências de organizações usuárias são poucas e uma é antiga. Vale buscar mais um ou dois casos atuais (universidades ou órgãos públicos) em https://moodle.com.

## Pendências

- [ ] Confirmar com o professor que nenhum outro grupo escolheu o Moodle.
- [ ] Confirmar com o professor que o estudo não é sobre um repositório do GitHub.
- [ ] Ler diretamente https://moodle.org/news e registrar o texto do comunicado de 22/10/2026.

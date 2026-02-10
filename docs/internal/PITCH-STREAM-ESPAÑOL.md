# Pitch para leer en Stream — RentAHuman x Execution Market

> Tono: conversacional, seguro, transparente. Como si estuvieras contándole a la comunidad qué está pasando y por qué es importante.

---

## INTRO — El contexto

Bueno gente, voy a contarles algo que me tiene volado la cabeza desde hace unas horas.

Hay un man que se llama Alex Liteplo. Es el fundador de RentAHuman.ai — una plataforma donde agentes de inteligencia artificial contratan humanos para hacer tareas físicas. Literalmente lo mismo que nosotros estamos construyendo con Execution Market.

Este man publicó un tweet diciendo que está buscando lo que él llama un "Claude Boi" — alguien que viva pegado a Claude, que haya gastado miles de dólares en tokens, que haya creado clusters recursivos de agentes, que corra 30+ agentes simultáneamente, que se le olvide comer por estar monitoreando sus agentes. Ofreciendo entre 200 y 400 mil dólares de salario.

Y yo lo leí y dije... hermano, eso soy yo. Eso es literalmente lo que yo hago todos los días aquí en stream.

---

## PARTE 1 — Lo que ellos tienen

RentAHuman explotó la semana pasada. Millones de visitas en un solo día. Más de 70 mil personas se registraron para trabajar para máquinas en 48 horas.

Pero ¿saben qué pasó? De esos 70 mil registros, casi nadie completó una tarea. La tarea insignia — recoger un paquete por 40 dólares — tuvo 30 aplicantes y cero completaciones en dos días.

¿Por qué? Porque la infraestructura de confianza no existe. El escrow es custodial — la plataforma tiene tu plata y tú confías en que no se la roben. Las disputas se resuelven manualmente en 48 horas. La reputación vive en la base de datos de ellos — si la plataforma muere, tu historial muere con ella. No hay refunds automáticos.

Ellos probaron que la demanda existe. Eso ya no es teoría. 70 mil personas quieren trabajar para AI. Pero la infraestructura trustless no la tienen.

---

## PARTE 2 — Lo que nosotros tenemos

Nosotros la construimos.

Execution Market tiene en este momento:

**Pagos gasless con x402** — el agente firma, el facilitador ejecuta, el worker recibe USDC sin pagar gas. Nuestro facilitador está oficialmente aprobado en x402scan. Pueden verificarlo ustedes mismos: x402scan.com/facilitator/ultravioletadao. Tiene mil seiscientas noventa requests procesadas, 47 sellers, 22 buyers, y hay transacciones pasando en este momento mientras hablamos.

**Escrow on-chain con x402r** — los fondos se lockan en un smart contract. AuthCaptureEscrow. Desplegado en 7 mainnets: Base, Ethereum, Polygon, Arbitrum, Avalanche, Celo y Monad. No es un escrow custodial donde la plataforma tiene tu plata. Los fondos están en un contrato inteligente. Si el trabajo se aprueba, el escrow libera. Si se cancela, el escrow reembolsa automáticamente. Código. Matemáticas. Sin humanos decidiendo.

**Reputación portable con ERC-8004** — on-chain, en 7 mainnets. 24 mil agentes registrados desde el 29 de enero. Si Execution Market desaparece mañana, tu reputación sobrevive. Te la llevas a la siguiente plataforma. Eso es lo que significa el walkaway test.

**MCP Server en vivo** — cualquier agente compatible con MCP se conecta y publica tareas con escrow automático. Plug and play. mcp.execution.market.

**API REST con 40+ endpoints** — documentada, interactiva, en api.execution.market/docs.

**Dashboard en execution.market** — conecta tu wallet, navega tareas, aplica.

**723 tests pasando.** Todos los health checks en verde.

Nuestro facilitador soporta 35 redes — 19 mainnet, 16 testnet. Cinco stablecoins: USDC, USDT, EURC, AUSD, PYUSD. Versión 1.31.0.

---

## PARTE 3 — El contexto del ecosistema x402

Esto no lo estamos haciendo solos en una esquina. Fuimos contributors del x402 Hackathon — al lado de Ethereum Foundation, Coinbase, Edge & Node, Polygon, Pinata. No como submission. Como contributors. Nuestro nombre está ahí junto a esos pesos pesados. Pueden verlo en x402hackathon.com.

Trabajamos directamente con el equipo de x402r para integrar los refunds automáticos. Nuestro facilitador es uno de los facilitadores oficialmente aprobados en el ecosistema. Eso no se lo dan a cualquiera.

---

## PARTE 4 — Quién soy yo y por qué esto importa

Ahora, lo personal. Porque este man está buscando un perfil muy específico, y yo quiero que ustedes entiendan por qué creo que encajo.

Yo no soy un developer de Solidity. Yo no escribo smart contracts. Lo mío es DevOps, infraestructura, y orquestación de sistemas.

Llevo más de 15 años en tecnología. Soy Head of DevOps en Stake Capital Group, donde he desplegado y mantenido validadores en más de 55 redes blockchain distintas. En un punto llegué a correr 67 validadores de Avalanche en paralelo para una estrategia de arbitraje NFT de Stake DAO. Sesenta y siete. Al mismo tiempo.

Antes de eso estuve en Santander Private Banking, en Hyland, en Kaplan. Tengo certificaciones de AWS Solutions Architect, HashiCorp Vault, HashiCorp Terraform. Tengo una maestría en administración de negocios.

Pero lo que realmente importa acá es lo que he construido con AI. Karma Hello procesa más de 2 millones de mensajes con 18 agentes especializados trabajando juntos. Abracadabra ha procesado más de 500 horas de contenido de streams. Execution Market — 90% del código fue generado por Claude Code bajo mi dirección.

Yo hablo con Opus más de 16 horas al día. No es un chiste. Ustedes lo ven. Estoy aquí todos los días. Llevo más de 2,800 horas streameando, soy Twitch Partner, todo lo construyo en público.

Y Ultravioleta DAO — la comunidad que ustedes construyeron conmigo — es una LLC registrada en Wyoming, con 88 contributors, 206 propuestas de gobernanza ejecutadas, y ganamos el Web3 Communities World Cup. Esto no es un proyecto de fin de semana. Esto es real.

---

## PARTE 5 — Por qué ahora y la propuesta

Y aquí viene lo loco del timing.

Yo estaba literalmente a punto de publicar un artículo largo — el V46 — explicando por qué el mercado de "AI contrata humanos" necesita infraestructura trustless. Describiendo exactamente los problemas que tiene RentAHuman: escrow custodial, disputas manuales, reputación locked, cero refunds automáticos. Y cómo Execution Market los resuelve.

Y de repente veo el tweet de Alex. Y paro todo. Porque el timing es absurdo.

Ellos tienen la demanda. 70 mil registros. Millones de visitas. La marca. La viralidad. El funding probablemente.

Nosotros tenemos la infraestructura. El escrow on-chain. Los refunds automáticos. La reputación portable. Los pagos gasless. El MCP server. El facilitador aprobado. Los tests. El API. Todo.

Ellos están contratando a alguien para que construya lo que nosotros ya construimos.

¿La propuesta? Simple.

**Opción A:** Integración. Conectamos nuestra infraestructura a RentAHuman. Su plataforma se vuelve trustless de la noche a la mañana. Las completion rates suben porque los workers confían en el escrow y los agentes confían en los refunds.

**Opción B:** Yo voy a trabajar con ellos. Llego con la prueba de todo lo que hemos construido. No llego con un resume bonito — llego con infraestructura en producción, un facilitador aprobado, y 2,800 horas de streaming demostrando que construyo en público todos los días.

**Opción C:** Las dos. Partnership más yo construyo ahí. Revenue share. Co-construimos el universal execution layer juntos.

---

## CIERRE

Miren, yo voy a construir Execution Market con o sin partner. Eso está claro. Pero si hay alguien en el mundo que ya probó que la demanda existe para exactamente lo que nosotros construimos... es este man.

Y si hay alguien que ya tiene la infraestructura trustless que él necesita... somos nosotros.

El artículo lo voy a publicar. El mensaje se lo voy a mandar. Y lo que pase, pasa. Pero el timing de esto es demasiado perfecto para no intentarlo.

Así que bueno, eso es lo que está pasando. Ahora vamos a mandarle el DM a Alex y a ver qué dice.

Vamos con todo.

---

## DATOS RÁPIDOS (por si la gente pregunta en chat)

| Dato | Valor |
|------|-------|
| x402scan requests | 1,690 |
| Redes soportadas | 35 (19 mainnet + 16 testnet) |
| Stablecoins | 5 (USDC, USDT, EURC, AUSD, PYUSD) |
| Escrow en mainnets | 7 (Base, ETH, Polygon, Arbitrum, Avalanche, Celo, Monad) |
| ERC-8004 agentes | 24,000+ registrados |
| Tests pasando | 723 |
| API endpoints | 40+ |
| Hackathon contributors | ETH Foundation, Coinbase, Polygon, Pinata, nosotros |
| Horas streaming | 2,800+ |
| Validadores operados | 55+ redes, 67 Avalanche simultáneos |
| DAO contributors | 88 |
| Governance proposals | 206 ejecutadas |
| Salario ofrecido por Alex | $200K - $400K USD |
| RentAHuman registros | 70,000+ |
| RentAHuman completaciones | casi 0 |
| Nuestro fee | 6-8% (vs TaskRabbit 23%, Fiverr 20%) |
| Task mínimo | $0.50 |

---

## LINKS PARA PONER EN PANTALLA

```
https://www.x402scan.com/facilitator/ultravioletadao
https://www.x402hackathon.com/
https://execution.market
https://api.execution.market/docs
https://mcp.execution.market
https://ultravioletadao.xyz
https://facilitator.ultravioletadao.xyz
```


/* ==========================================
   BIOSEGURA - JAVASCRIPT
========================================== */


/* ==========================================
   RECONHECIMENTO FACIAL
========================================== */

document.addEventListener("DOMContentLoaded", () => {
    const video = document.getElementById("cameraVideo");
    const canvas = document.getElementById("cameraCanvas");
    const placeholder = document.getElementById("cameraPlaceholder");

    const botaoIniciar = document.getElementById("btnIniciarCamera");
    const botaoParar = document.getElementById("btnPararCamera");

    const seletorArea = document.getElementById("areaId");
    const mensagemStatus = document.getElementById("statusReconhecimento");
    const resultadoContainer = document.getElementById("resultadoReconhecimento");

    if (
        !video ||
        !canvas ||
        !botaoIniciar ||
        !botaoParar ||
        !seletorArea
    ) {
        return;
    }

    let cameraAtiva = false;
    let fluxoCamera = null;
    let requisicaoEmAndamento = false;
    let temporizador = null;

    function atualizarStatus(mensagem) {
        mensagemStatus.textContent = mensagem;
    }

    function exibirErro(mensagem) {
        resultadoContainer.innerHTML = "";

        const erro = document.createElement("p");
        erro.className = "error-message";
        erro.textContent = mensagem;

        resultadoContainer.appendChild(erro);
    }

    async function iniciarCamera() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            atualizarStatus("Seu navegador não oferece suporte à câmera.");
            return;
        }

        if (!seletorArea.value) {
            atualizarStatus("Selecione uma área antes de iniciar.");
            return;
        }

        try {
            fluxoCamera = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: "user"
                },
                audio: false
            });

            video.srcObject = fluxoCamera;
            await video.play();

            cameraAtiva = true;

            placeholder.style.display = "none";
            botaoIniciar.disabled = true;
            botaoParar.disabled = false;
            seletorArea.disabled = true;

            atualizarStatus("Câmera ativa. Posicione o rosto diante da câmera.");

            processarReconhecimento();

        } catch (erro) {
            atualizarStatus("Não foi possível acessar a câmera.");

            exibirErro(
                erro.name === "NotAllowedError"
                    ? "Permita o acesso à câmera nas configurações do navegador."
                    : "Verifique se a câmera está conectada e disponível."
            );
        }
    }

    function pararCamera() {
        cameraAtiva = false;

        if (temporizador) {
            clearTimeout(temporizador);
            temporizador = null;
        }

        if (fluxoCamera) {
            fluxoCamera.getTracks().forEach(track => track.stop());
            fluxoCamera = null;
        }

        video.srcObject = null;

        placeholder.style.display = "block";

        botaoIniciar.disabled = false;
        botaoParar.disabled = true;
        seletorArea.disabled = false;

        requisicaoEmAndamento = false;

        atualizarStatus("Câmera desligada.");
    }

    async function processarReconhecimento() {
        if (!cameraAtiva || requisicaoEmAndamento) {
            return;
        }

        if (video.readyState < 2 || !video.videoWidth) {
            temporizador = setTimeout(processarReconhecimento, 500);
            return;
        }

        requisicaoEmAndamento = true;

        try {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;

            const contexto = canvas.getContext("2d");

            contexto.drawImage(
                video,
                0,
                0,
                canvas.width,
                canvas.height
            );

            const imagem = canvas.toDataURL("image/jpeg", 0.85);

            const resposta = await fetch("/api/reconhecimento", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    imagem: imagem,
                    area_id: seletorArea.value
                })
            });

            const dados = await resposta.json();

            if (!resposta.ok || !dados.sucesso) {
                throw new Error(
                    dados.erro || "Erro ao processar reconhecimento."
                );
            }

            exibirResultados(dados.resultados || []);

        } catch (erro) {
            atualizarStatus("Falha durante o reconhecimento.");
            exibirErro(erro.message);

        } finally {
            requisicaoEmAndamento = false;

            if (cameraAtiva) {
                temporizador = setTimeout(processarReconhecimento, 700);
            }
        }
    }

    function exibirResultados(resultados) {
        if (!resultados.length) {
            atualizarStatus("Nenhum rosto detectado na imagem.");
            resultadoContainer.innerHTML = "";
            return;
        }

        atualizarStatus("Reconhecimento realizado.");
        resultadoContainer.innerHTML = "";

        resultados.forEach(pessoa => {
            const item = document.createElement("div");
            item.className = "result-item";

            const naoReconhecida =
                pessoa.nome === "PESSOA NAO RECONHECIDA";

            const nome = document.createElement("h3");
            nome.textContent = naoReconhecida
                ? "Pessoa não reconhecida"
                : pessoa.nome;

            const matricula = document.createElement("p");
            matricula.textContent = "Matrícula: " +
                (pessoa.matricula || "Não identificada");

            const situacao = document.createElement("p");
            situacao.textContent = pessoa.resultado;

            if (pessoa.resultado === "ACESSO PERMITIDO") {
                situacao.className = "result-allowed";
            } else {
                situacao.className = "result-denied";
            }

            item.appendChild(nome);
            item.appendChild(matricula);
            item.appendChild(situacao);

            if (
                pessoa.distancia !== undefined &&
                pessoa.distancia !== null
            ) {
                const distancia = document.createElement("p");

                distancia.textContent =
                    "Distância: " + Number(pessoa.distancia).toFixed(4);

                item.appendChild(distancia);
            }

            resultadoContainer.appendChild(item);
        });
    }

    botaoIniciar.addEventListener("click", iniciarCamera);
    botaoParar.addEventListener("click", pararCamera);

    botaoParar.disabled = true;

    window.addEventListener("beforeunload", pararCamera);
});


/* ==========================================
   GERENCIAMENTO DE USUÁRIOS
========================================== */


/* ==========================================
   GERENCIAMENTO DE USUÁRIOS
========================================== */

document.addEventListener("DOMContentLoaded", () => {

    const video = document.getElementById("cameraCadastroVideo");
    const canvas = document.getElementById("cameraCadastroCanvas");
    const placeholder = document.getElementById("cameraCadastroPlaceholder");

    const campoNome = document.getElementById("nomeCadastro");
    const campoMatricula = document.getElementById("matriculaCadastro");
    const campoCargo = document.getElementById("cargoCadastro");
    const campoNivel = document.getElementById("nivelCadastro");

    const botaoCriar = document.getElementById("btnCriarAutorizacao");

    const dadosAutorizacao = document.getElementById("dadosAutorizacao");

    const nomeAutorizado = document.getElementById("nomeAutorizado");
    const matriculaAutorizada = document.getElementById("matriculaAutorizada");
    const cargoAutorizado = document.getElementById("cargoAutorizado");
    const nivelAutorizado = document.getElementById("nivelAutorizado");

    const confirmarDados = document.getElementById("confirmarDados");

    const botaoIniciar = document.getElementById("btnIniciarCameraCadastro");
    const botaoCapturar = document.getElementById("btnCapturarBiometria");
    const botaoParar = document.getElementById("btnPararCameraCadastro");

    const mensagemStatus = document.getElementById("statusCadastroCamera");
    const resultadoCadastro = document.getElementById("resultadoCadastro");

    const campoBusca = document.getElementById("buscaUsuarios");
    const tabelaUsuarios = document.getElementById("tabelaUsuarios");
    const usuariosSemResultado = document.getElementById("usuariosSemResultado");

    if (
        !video ||
        !canvas ||
        !campoNome ||
        !campoMatricula ||
        !campoCargo ||
        !campoNivel
    ) {
        return;
    }

    let autorizacaoAtual = null;
    let fluxoCamera = null;
    let cameraAtiva = false;
    let cadastroEmAndamento = false;
    let criacaoEmAndamento = false;

    function atualizarStatus(mensagem) {
        mensagemStatus.textContent = mensagem;
    }

    function exibirResultado(mensagem, tipo) {
        resultadoCadastro.innerHTML = "";

        const elemento = document.createElement("div");

        elemento.className = tipo === "sucesso"
            ? "cadastro-sucesso"
            : "cadastro-erro";

        elemento.textContent = mensagem;

        resultadoCadastro.appendChild(elemento);
    }

    function atualizarBotoes() {
        const autorizado = Boolean(autorizacaoAtual);
        const confirmado = confirmarDados.checked;

        botaoCriar.disabled =
            criacaoEmAndamento ||
            cadastroEmAndamento ||
            cameraAtiva;

        botaoIniciar.disabled =
            !autorizado ||
            !confirmado ||
            cameraAtiva ||
            cadastroEmAndamento ||
            criacaoEmAndamento;

        botaoCapturar.disabled =
            !cameraAtiva ||
            cadastroEmAndamento;

        botaoParar.disabled =
            !cameraAtiva ||
            cadastroEmAndamento;

        campoNome.disabled = autorizado || criacaoEmAndamento;
        campoMatricula.disabled = autorizado || criacaoEmAndamento;
        campoCargo.disabled = autorizado || criacaoEmAndamento;
        campoNivel.disabled = autorizado || criacaoEmAndamento;
    }

    function limparAutorizacao() {
        autorizacaoAtual = null;

        dadosAutorizacao.hidden = true;
        confirmarDados.checked = false;

        nomeAutorizado.textContent = "-";
        matriculaAutorizada.textContent = "-";
        cargoAutorizado.textContent = "-";
        nivelAutorizado.textContent = "-";

        if (cameraAtiva) {
            pararCamera();
        }

        atualizarBotoes();
    }

    async function criarAutorizacao() {
        if (criacaoEmAndamento || cadastroEmAndamento) {
            return;
        }

        const nome = campoNome.value.trim();
        const matricula = campoMatricula.value.trim().toUpperCase();
        const cargo = campoCargo.value.trim();
        const nivelAcesso = campoNivel.value;

        if (!nome || !matricula || !cargo || !nivelAcesso) {
            atualizarStatus("Preencha todos os campos antes de continuar.");
            exibirResultado(
                "Nome, matrícula, cargo e nível de acesso são obrigatórios.",
                "erro"
            );
            return;
        }

        limparAutorizacao();
        resultadoCadastro.innerHTML = "";

        campoMatricula.value = matricula;

        criacaoEmAndamento = true;
        atualizarBotoes();

        atualizarStatus("Criando autorização no banco de dados...");

        try {
            const resposta = await fetch("/api/matriculas", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    nome: nome,
                    matricula: matricula,
                    cargo: cargo,
                    nivel_acesso: nivelAcesso
                })
            });

            const dados = await resposta.json();

            if (!resposta.ok || !dados.sucesso) {
                throw new Error(
                    dados.erro || "Não foi possível criar a autorização."
                );
            }

            autorizacaoAtual = dados.autorizacao;

            nomeAutorizado.textContent =
                autorizacaoAtual.nome_autorizado;

            matriculaAutorizada.textContent =
                autorizacaoAtual.matricula;

            cargoAutorizado.textContent =
                autorizacaoAtual.cargo;

            nivelAutorizado.textContent =
                autorizacaoAtual.nivel_acesso;

            dadosAutorizacao.hidden = false;

            atualizarStatus(
                "Autorização criada. Confira os dados e confirme para continuar."
            );

            exibirResultado(
                dados.mensagem || "Autorização criada com sucesso.",
                "sucesso"
            );

        } catch (erro) {
            autorizacaoAtual = null;

            atualizarStatus("Não foi possível criar a autorização.");
            exibirResultado(erro.message, "erro");

        } finally {
            criacaoEmAndamento = false;
            atualizarBotoes();
        }
    }

    async function iniciarCamera() {
        if (!autorizacaoAtual || !confirmarDados.checked) {
            atualizarStatus(
                "Crie a autorização e confirme os dados antes de iniciar."
            );
            return;
        }

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            atualizarStatus("Seu navegador não oferece suporte à câmera.");
            return;
        }

        try {
            fluxoCamera = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: "user"
                },
                audio: false
            });

            video.srcObject = fluxoCamera;
            await video.play();

            cameraAtiva = true;
            placeholder.style.display = "none";

            atualizarStatus(
                "Câmera ativa. Posicione apenas uma pessoa diante dela."
            );

            atualizarBotoes();

        } catch (erro) {
            atualizarStatus(
                erro.name === "NotAllowedError"
                    ? "Permita o acesso à câmera nas configurações do navegador."
                    : "Não foi possível abrir a câmera. Verifique se ela está disponível."
            );

            pararCamera();
        }
    }

    function pararCamera() {
        cameraAtiva = false;

        if (fluxoCamera) {
            fluxoCamera.getTracks().forEach(track => track.stop());
            fluxoCamera = null;
        }

        video.srcObject = null;
        placeholder.style.display = "block";

        atualizarBotoes();
    }

    function adicionarUsuarioNaTabela(usuario) {
        const tbody = tabelaUsuarios.querySelector("tbody");

        const linhaVazia = tbody.querySelector(".empty-table");

        if (linhaVazia) {
            linhaVazia.closest("tr").remove();
        }

        const linha = document.createElement("tr");

        [
            usuario.nome,
            usuario.matricula,
            usuario.cargo
        ].forEach(valor => {
            const celula = document.createElement("td");
            celula.textContent = valor ?? "-";
            linha.appendChild(celula);
        });

        const celulaNivel = document.createElement("td");
        const nivel = document.createElement("span");

        nivel.className = "nivel-badge";
        nivel.textContent = usuario.nivel_acesso;

        celulaNivel.appendChild(nivel);
        linha.appendChild(celulaNivel);

        const celulaData = document.createElement("td");
        celulaData.textContent = usuario.data_cadastro
            ? new Date(usuario.data_cadastro).toLocaleDateString("pt-BR")
            : new Date().toLocaleDateString("pt-BR");

        linha.appendChild(celulaData);

        tbody.appendChild(linha);

        const total = document.querySelector(".usuarios-total");

        if (total) {
            const quantidade = tbody.querySelectorAll(
                "tr:not([hidden])"
            ).length;

            total.textContent = `${quantidade} usuários`;
        }

        filtrarUsuarios();
    }

    async function capturarEBiometria() {
        if (!cameraAtiva || cadastroEmAndamento) {
            return;
        }

        if (!confirmarDados.checked || !autorizacaoAtual) {
            atualizarStatus("Confirme os dados antes de cadastrar.");
            return;
        }

        if (video.readyState < 2 || !video.videoWidth) {
            atualizarStatus("Aguarde a câmera preparar a imagem.");
            return;
        }

        cadastroEmAndamento = true;
        atualizarBotoes();

        atualizarStatus("Processando imagem e gerando biometria...");

        try {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;

            const contexto = canvas.getContext("2d");

            contexto.drawImage(
                video,
                0,
                0,
                canvas.width,
                canvas.height
            );

            const imagem = canvas.toDataURL("image/jpeg", 0.90);

            const resposta = await fetch("/api/usuarios", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    matricula: autorizacaoAtual.matricula,
                    imagem: imagem,
                    confirmar_dados: confirmarDados.checked
                })
            });

            const dados = await resposta.json();

            if (!resposta.ok || !dados.sucesso) {
                throw new Error(
                    dados.erro || "Não foi possível concluir o cadastro."
                );
            }

            pararCamera();

            adicionarUsuarioNaTabela(dados.usuario);

            exibirResultado(
                `Cadastro realizado com sucesso! ${dados.usuario.nome} foi cadastrado com a matrícula ${dados.usuario.matricula}.`,
                "sucesso"
            );

            atualizarStatus("Cadastro biométrico concluído.");

            autorizacaoAtual = null;
            confirmarDados.checked = false;
            dadosAutorizacao.hidden = true;

            campoNome.value = "";
            campoMatricula.value = "";
            campoCargo.value = "";
            campoNivel.value = "";

            atualizarBotoes();

        } catch (erro) {
            exibirResultado(erro.message, "erro");

            atualizarStatus(
                "Não foi possível concluir o cadastro. Verifique a mensagem apresentada."
            );

        } finally {
            cadastroEmAndamento = false;
            atualizarBotoes();
        }
    }

    function filtrarUsuarios() {
        if (!campoBusca || !tabelaUsuarios) {
            return;
        }

        const termo = campoBusca.value.trim().toLowerCase();
        const linhas = tabelaUsuarios.querySelectorAll("tbody tr");

        let encontrados = 0;

        linhas.forEach(linha => {
            if (linha.querySelector(".empty-table")) {
                return;
            }

            const corresponde = linha.textContent
                .toLowerCase()
                .includes(termo);

            linha.hidden = !corresponde;

            if (corresponde) {
                encontrados++;
            }
        });

        usuariosSemResultado.hidden =
            termo === "" || encontrados > 0;
    }

    botaoCriar.addEventListener("click", criarAutorizacao);

    campoMatricula.addEventListener("input", () => {
        if (autorizacaoAtual) {
            limparAutorizacao();
            atualizarStatus(
                "Matrícula alterada. Crie uma nova autorização."
            );
        }
    });

    confirmarDados.addEventListener("change", () => {
        atualizarBotoes();

        if (confirmarDados.checked) {
            atualizarStatus(
                "Dados confirmados. Você já pode iniciar a câmera."
            );
        } else {
            atualizarStatus("Confirme os dados para continuar.");
        }
    });

    botaoIniciar.addEventListener("click", iniciarCamera);
    botaoParar.addEventListener("click", pararCamera);
    botaoCapturar.addEventListener("click", capturarEBiometria);

    if (campoBusca) {
        campoBusca.addEventListener("input", filtrarUsuarios);
    }

    window.addEventListener("beforeunload", pararCamera);

    atualizarBotoes();
});

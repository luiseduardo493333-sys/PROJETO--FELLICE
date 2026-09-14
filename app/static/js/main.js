// ================= CONTROLE GLOBAL DE MODAIS =================
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.remove('active');
    // Só restaura overflow se não houver outro modal ou drawer aberto
    if (!document.querySelector('.modal-backdrop.active') && !document.querySelector('.drawer-container.active')) {
      document.body.style.overflow = '';
    }
  }
}

// ================= CONTROLE DO MENU DRAWER MOBILE =================
function openDrawer() {
  const drawer = document.getElementById('mobileDrawer');
  const backdrop = document.getElementById('mobileDrawerBackdrop');
  if (drawer) drawer.classList.add('active');
  if (backdrop) backdrop.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeDrawer() {
  const drawer = document.getElementById('mobileDrawer');
  const backdrop = document.getElementById('mobileDrawerBackdrop');
  if (drawer) drawer.classList.remove('active');
  if (backdrop) backdrop.classList.remove('active');
  if (!document.querySelector('.modal-backdrop.active')) {
    document.body.style.overflow = '';
  }
}

// Fechar com tecla ESC
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-backdrop.active').forEach(m => {
      m.classList.remove('active');
    });
    closeDrawer();
    document.body.style.overflow = '';
  }
});

// Fechar modal clicando no backdrop escurecido
document.addEventListener('click', (e) => {
  if (e.target.classList && e.target.classList.contains('modal-backdrop')) {
    e.target.classList.remove('active');
    if (!document.querySelector('.drawer-container.active')) {
      document.body.style.overflow = '';
    }
  }
});

// Helper para preenchimento de Modal de Edição de Produto
function abrirModalEditarProduto(id, nome, categoria, sku) {
  const form = document.getElementById('formEditarProduto');
  if (form) {
    form.action = `/produtos/${id}/editar`;
    document.getElementById('edit_prod_nome').value = nome || '';
    document.getElementById('edit_prod_categoria').value = categoria || '';
    document.getElementById('edit_prod_sku').value = sku || '';
    openModal('modalEditarProduto');
  }
}

// Helper para Modal de Transferência de Colaborador
function abrirModalTransferirUsuario(id, nome, lojaAtualNome, lojaAtualId) {
  const form = document.getElementById('formTransferirUsuario');
  if (form) {
    form.action = `/usuarios/${id}/transferir`;
    document.getElementById('transf_usuario_nome').textContent = nome;
    document.getElementById('transf_loja_atual').textContent = lojaAtualNome;
    const select = document.getElementById('transf_nova_loja');
    if (select) {
      // Evita selecionar a mesma loja
      for (let opt of select.options) {
        opt.disabled = (opt.value === String(lojaAtualId));
      }
      select.value = '';
    }
    openModal('modalTransferirUsuario');
  }
}

// Script JavaScript auxiliar do sistema Fellice
document.addEventListener('DOMContentLoaded', () => {
  // Auto-cálculo dinâmico na tela/modal de contagem física
  const camposContagem = document.querySelectorAll('.input-contagem-fisica');
  camposContagem.forEach(input => {
    input.addEventListener('input', (e) => {
      const row = e.target.closest('tr');
      const esperado = parseFloat(row.dataset.esperado || 0);
      const digitado = parseFloat(e.target.value.replace(',', '.') || 0);
      const diffEl = row.querySelector('.diff-valor');
      const obsInput = row.querySelector('.input-obs');

      if (!isNaN(digitado) && e.target.value.trim() !== '') {
        const diferenca = digitado - esperado;
        diffEl.textContent = (diferenca > 0 ? '+' : '') + Math.round(diferenca) + ' UN';
        if (Math.abs(diferenca) > 0.001) {
          diffEl.className = 'diff-valor badge ' + (diferenca < 0 ? 'badge-danger' : 'badge-warning');
          if (obsInput) {
            obsInput.required = true;
            obsInput.placeholder = 'Obrigatório: Justifique a divergência...';
          }
        } else {
          diffEl.className = 'diff-valor badge badge-success';
          if (obsInput) {
            obsInput.required = false;
            obsInput.placeholder = 'Sem divergência apurada';
          }
        }
      } else {
        diffEl.textContent = '-';
        diffEl.className = 'diff-valor';
      }
    });
  });

  // Alerta em entradas quando recebido != esperado
  const inputRecebido = document.getElementById('quantidade_recebida');
  const inputEsperado = document.getElementById('quantidade_esperada');
  const divAlerta = document.getElementById('alerta-divergencia-entrada');
  const inputMotivo = document.getElementById('motivo_divergencia');

  function checarDivergenciaEntrada() {
    if (!inputRecebido || !inputEsperado) return;
    const rec = parseFloat(inputRecebido.value.replace(',', '.') || 0);
    const esp = parseFloat(inputEsperado.value.replace(',', '.') || 0);

    if (esp > 0 && Math.abs(rec - esp) > 0.001) {
      if (divAlerta) divAlerta.style.display = 'block';
      if (inputMotivo) inputMotivo.required = true;
    } else {
      if (divAlerta) divAlerta.style.display = 'none';
      if (inputMotivo) inputMotivo.required = false;
    }
  }

  if (inputRecebido && inputEsperado) {
    inputRecebido.addEventListener('input', checarDivergenciaEntrada);
    inputEsperado.addEventListener('input', checarDivergenciaEntrada);
  }

  // Verifica se a URL tem instrução para abrir modal automático
  const params = new URLSearchParams(window.location.search);
  if (params.get('modal')) {
    openModal(params.get('modal'));
  }
});

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# 1. Configuração da Página
st.set_page_config(page_title="Administradoras | MRC Imóveis", page_icon="🏢", layout="wide")

try:
    st.image("https://raw.githubusercontent.com/mrcimoveis-coder/portal-intranet/main/logo.jpeg", width=260)
except:
    pass

# 2. Conexão Google Sheets
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def conectar_google_sheets():
    credenciais_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in credenciais_dict:
        credenciais_dict["private_key"] = credenciais_dict["private_key"].replace("\\n", "\n")
    
    credentials = Credentials.from_service_account_info(credenciais_dict, scopes=SCOPES)
    client = gspread.authorize(credentials)
    return client.open_by_key("15-ilgG_5sxKAkcR8STzu9aRE76UlEIKwXCnDeN6rmss").sheet1

# 3. Autenticação por Senha
SENHA_CORRETA = "431360"

if "autenticado_adm" not in st.session_state:
    st.session_state.autenticado_adm = False

if not st.session_state.autenticado_adm:
    st.title("🔒 Acesso Restrito — Administradoras")
    senha_input = st.text_input("Digite a senha de acesso interno:", type="password")
    if st.button("Entrar", type="primary"):
        if senha_input == SENHA_CORRETA:
            st.session_state.autenticado_adm = True
            st.rerun()
        else:
            st.error("❌ Senha incorreta.")
    st.stop()

# 4. Interface e Ações
try:
    sheet = conectar_google_sheets()
except Exception as e:
    st.error(f"❌ Erro ao conectar com o Google Sheets: {e}")
    st.stop()

st.title("🏢 Gestão de Administradoras de Condomínio")
st.write("Consulta rápida de contatos, senhas e vínculos de imóveis da carteira MRC.")

aba_consulta, aba_cadastro, aba_editar = st.tabs(["🔍 Consultar Administradoras", "➕ Cadastrar Novo Vínculo", "✏️ Editar / Excluir"])

# --- ABA 1: CONSULTA ---
with aba_consulta:
    st.subheader("Buscar Administradora ou Imóvel")
    try:
        dados_raw = sheet.get_all_records()
        if not dados_raw:
            st.info("Nenhuma administradora cadastrada até o momento.")
        else:
            df = pd.DataFrame(dados_raw)
            busca = st.text_input("🔎 Digite o nome da Administradora, Imóvel, Locador ou Locatário:")
            
            if busca:
                termo = busca.lower()
                df_filtrado = df[df.apply(lambda row: row.astype(str).str.lower().str.contains(termo).any(), axis=1)]
            else:
                df_filtrado = df
                
            st.write(f"**Total de registros encontrados:** {len(df_filtrado)}")
            
            colunas_exibicao = ["Administradora", "Contato Preferencial", "Telefone / WhatsApp", "E-mail", "Imóvel Locado", "Locatário", "Locador", "Senhas e Observações"]
            colunas_existentes = [col for col in colunas_exibicao if col in df_filtrado.columns]
            
            st.dataframe(df_filtrado[colunas_existentes], use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")

# --- ABA 2: CADASTRO ---
with aba_cadastro:
    st.subheader("Adicionar Nova Administradora / Imóvel")
    with st.form("form_nova_adm", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            administradora = st.text_input("Nome da Administradora *")
            contato_pref = st.selectbox("Contato Preferencial", ["WHATSAPP", "E-MAIL", "TELEFONE", "SITE / PORTAL", "OUTRO"])
            telefone = st.text_input("Telefone / WhatsApp")
            email = st.text_input("E-mail da Administradora")
        with col2:
            imovel = st.text_input("Endereço do Imóvel Vinculado *")
            locatario = st.text_input("Nome do Locatário")
            locador = st.text_input("Nome do Locador")
            
        obs = st.text_area("Senhas de site, ramal ou observações adicionais")
        btn_salvar = st.form_submit_button("💾 Salvar Cadastro", type="primary")
        
        if btn_salvar:
            if not administradora or not imovel:
                st.error("⚠️ Os campos 'Administradora' e 'Imóvel Locado' são obrigatórios.")
            else:
                try:
                    nova_linha = [administradora, imovel, locatario, locador, contato_pref, telefone, email, obs]
                    sheet.append_row(nova_linha)
                    st.success(f"✅ Administradora **{administradora}** cadastrada com sucesso!")
                    st.balloons()
                except Exception as e:
                    st.error(f"❌ Erro ao salvar no Google Sheets: {e}")

# --- ABA 3: EDIÇÃO E EXCLUSÃO (MELHORADA COM BUSCA INTELIGENTE) ---
with aba_editar:
    st.subheader("Alterar ou Excluir Registro")
    try:
        dados_raw = sheet.get_all_records()
        if dados_raw:
            df = pd.DataFrame(dados_raw)
            
            # Campo de busca em texto livre
            kw_ed = st.text_input("🔎 Pesquisar para localizar o registro (Administradora, Imóvel, Locador ou Locatário):", key="search_editar_adm")
            
            df_e = df.copy()
            if kw_ed:
                termo_ed = kw_ed.lower()
                mask_e = df_e.apply(lambda r: r.astype(str).str.lower().str.contains(termo_ed).any(), axis=1)
                df_e = df_e[mask_e]
                
            if df_e.empty:
                st.warning("⚠️ Nenhum registro encontrado com esse termo de pesquisa.")
            else:
                # Cria um dicionário seguro mapeando o rótulo de exibição para o índice real do dataframe
                options_dict_e = {}
                for idx_e, row_e in df_e.iterrows():
                    lbl = f"🏢 {row_e.get('Administradora', 'N/I')} | 📍 {row_e.get('Imóvel Locado', 'N/I')} | 👤 {row_e.get('Locatário', 'N/I')}"
                    options_dict_e[lbl] = idx_e
                    
                item_e_lbl = st.selectbox("Selecione o registro exato que deseja gerenciar:", [""] + list(options_dict_e.keys()))
                
                if item_e_lbl:
                    idx_e = options_dict_e[item_e_lbl]
                    dados_atuais = df.iloc[idx_e]
                    linha_real = idx_e + 2  # Acha a linha exata no Sheets
                    
                    st.markdown("---")
                    
                    # --- BLOCO DE EDIÇÃO ---
                    with st.form("form_editar_dados"):
                        st.info(f"✏️ Editando dados da administradora: **{dados_atuais.get('Administradora', '')}**")
                        col_edit1, col_edit2 = st.columns(2)
                        
                        with col_edit1:
                            novo_imovel = st.text_input("Endereço do Imóvel Vinculado", value=str(dados_atuais.get("Imóvel Locado", "")))
                            novo_locatario = st.text_input("Locatário", value=str(dados_atuais.get("Locatário", "")))
                            novo_locador = st.text_input("Locador", value=str(dados_atuais.get("Locador", "")))
                            
                            opcoes_contato = ["WHATSAPP", "E-MAIL", "TELEFONE", "SITE / PORTAL", "OUTRO"]
                            contato_atual = str(dados_atuais.get("Contato Preferencial", "E-MAIL")).upper()
                            index_contato = opcoes_contato.index(contato_atual) if contato_atual in opcoes_contato else 4
                            novo_contato_pref = st.selectbox("Contato Preferencial", opcoes_contato, index=index_contato)
                        
                        with col_edit2:
                            novo_adm = st.text_input("Nome da Administradora", value=str(dados_atuais.get("Administradora", "")))
                            novo_tel = st.text_input("Telefone / WhatsApp", value=str(dados_atuais.get("Telefone / WhatsApp", "")))
                            novo_email = st.text_input("E-mail", value=str(dados_atuais.get("E-mail", "")))
                            nova_senha = st.text_area("Senhas e Observações", value=str(dados_atuais.get("Senhas e Observações", "")))
                        
                        btn_atualizar = st.form_submit_button("🔄 Confirmar Alterações", type="primary")
                        
                        if btn_atualizar:
                            sheet.update_cell(linha_real, 1, novo_adm)
                            sheet.update_cell(linha_real, 2, novo_imovel)
                            sheet.update_cell(linha_real, 3, novo_locatario)
                            sheet.update_cell(linha_real, 4, novo_locador)
                            sheet.update_cell(linha_real, 5, novo_contato_pref)
                            sheet.update_cell(linha_real, 6, novo_tel)
                            sheet.update_cell(linha_real, 7, novo_email)
                            sheet.update_cell(linha_real, 8, nova_senha)
                            st.success("✅ Dados atualizados com sucesso!")
                            st.rerun()
                    
                    # --- BLOCO DE EXCLUSÃO ---
                    st.markdown("---")
                    st.markdown("### ❌ Excluir Imóvel do Sistema")
                    st.warning("Cuidado: Esta ação apagará permanentemente o imóvel e todos os contatos desta administradora da planilha.")
                    
                    # Trava de segurança
                    confirmar_exclusao = st.checkbox("Tenho certeza que desejo excluir este registro")
                    
                    if confirmar_exclusao:
                        if st.button("🗑️ Apagar Registro Definitivamente", type="primary"):
                            sheet.delete_row(linha_real)  # Deleta a linha direto no Google Sheets
                            st.success("✅ Registro excluído com sucesso!")
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            st.rerun()
                            
    except Exception as e:
        st.error(f"Erro ao carregar módulo de edição: {e}")

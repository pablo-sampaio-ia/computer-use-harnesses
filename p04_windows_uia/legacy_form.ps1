# "Sistema legado" desktop de brinquedo (Windows Forms): cadastro de clientes.
# Cada cadastro e anexado como JSON em -OutFile (o verificador le esse arquivo).
#   powershell -STA -File legacy_form.ps1 -OutFile C:\caminho\clientes.jsonl
param([string]$OutFile = "$env:TEMP\clientes.jsonl")
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$f = New-Object Windows.Forms.Form
$f.Text = "Sistema Legado - Cadastro"; $f.Size = New-Object Drawing.Size(460, 330); $f.StartPosition = "CenterScreen"

function Add-Field($label, $name, $y) {
  $l = New-Object Windows.Forms.Label; $l.Text = $label; $l.Location = New-Object Drawing.Point(20, $y); $l.AutoSize = $true
  $t = New-Object Windows.Forms.TextBox; $t.Name = $name; $t.AccessibleName = $label
  $t.Location = New-Object Drawing.Point(140, ($y - 3)); $t.Width = 270
  $f.Controls.AddRange(@($l, $t)); return $t
}
$nome  = Add-Field "Nome completo" "txtNome" 25
$email = Add-Field "E-mail" "txtEmail" 65
$tel   = Add-Field "Telefone" "txtTelefone" 105

$l = New-Object Windows.Forms.Label; $l.Text = "Tipo"; $l.Location = New-Object Drawing.Point(20, 145); $l.AutoSize = $true
$tipo = New-Object Windows.Forms.ComboBox; $tipo.Name = "cmbTipo"; $tipo.AccessibleName = "Tipo"
$tipo.DropDownStyle = "DropDownList"; $tipo.Items.AddRange(@("Pessoa fisica", "Empresa")); $tipo.SelectedIndex = 0
$tipo.Location = New-Object Drawing.Point(140, 142); $tipo.Width = 270
$f.Controls.AddRange(@($l, $tipo))

$status = New-Object Windows.Forms.Label; $status.Name = "lblStatus"
$status.Location = New-Object Drawing.Point(20, 250); $status.AutoSize = $true; $status.Text = "Pronto."
$f.Controls.Add($status)

$btn = New-Object Windows.Forms.Button; $btn.Name = "btnSalvar"; $btn.Text = "Salvar cliente"
$btn.Location = New-Object Drawing.Point(140, 190); $btn.Width = 150
$btn.Add_Click({
  $rec = [ordered]@{ nome = $nome.Text; email = $email.Text; telefone = $tel.Text; tipo = $tipo.Text }
  ($rec | ConvertTo-Json -Compress) | Add-Content -Path $OutFile -Encoding UTF8
  $status.Text = "Cliente " + $nome.Text + " salvo."
  $nome.Text = ""; $email.Text = ""; $tel.Text = ""
})
$f.Controls.Add($btn)
[void]$f.ShowDialog()

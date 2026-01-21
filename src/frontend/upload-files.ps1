$STACK_BACKEND = "app-backend"
$STACK_FRONTEND = "frontend"
$REGION = "us-east-1"
$FRONTEND_DIR = "./src/frontend"

Write-Host "--- Iniciando despliegue de archivos frontend ---" -ForegroundColor Cyan

Write-Host "Obteniendo URL de la API..."
$API_URL = aws cloudformation describe-stacks `
    --stack-name $STACK_BACKEND `
    --region $REGION `
    --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayApi'].OutputValue" `
    --output text

if ($null -eq $API_URL -or $API_URL -eq "") {
    Write-Error "No se pudo obtener la URL. ¿Has desplegado el stack '$STACK_BACKEND'?"
    exit
}

$CONFIG_PATH = "$FRONTEND_DIR/config.json"
$CONFIG_OBJ = @{ API_URL = $API_URL }
$CONFIG_OBJ | ConvertTo-Json | Out-File -FilePath $CONFIG_PATH -Encoding ascii
Write-Host "Archivo config.json generado correctamente." -ForegroundColor Green

$BUCKET_NAME = aws cloudformation describe-stacks `
    --stack-name $STACK_FRONTEND `
    --region $REGION `
    --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" `
    --output text

Write-Host "Subiendo archivos al bucket: $BUCKET_NAME..."
aws s3 sync $FRONTEND_DIR "s3://$BUCKET_NAME" `
    --region $REGION `
    --exclude "*.ps1" `
    --delete

Write-Host "--- Despliegue completado con éxito ---" -ForegroundColor Cyan
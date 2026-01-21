document.addEventListener('DOMContentLoaded', async () => {
    let API_URL = "";
    try {
        const configResponse = await fetch('config.json');
        const configData = await configResponse.json();
        API_URL = configData.API_URL;
        console.log("Conectado a la API:", API_URL);
    } catch (error) {
        console.error("Error cargando configuración:", error);
    }

   const form = document.getElementById('formRegistro');
   const btnBuscar = document.getElementById('btnBuscar');
   const mainModal = new bootstrap.Modal(document.getElementById('mainModal'));
   
   const regex = {
       dni: /^[0-9]{8}[A-Z]$/i,
       email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
       matricula: /^[0-9]{4}[A-Z]{3}$/i 
   };

   // --- EVENTO: REGISTRO (POST) ---
   form.addEventListener('submit', async (event) => {
       event.preventDefault();

       if (!validarVacios()) return;

       if (validarFormatos()) {
           const data = capturarDatos();
           
           try {
               // LLAMADA FETCH POST
               const response = await fetch(`${API_URL}crear`, {
                   method: 'POST',
                   headers: {
                       'Content-Type': 'application/json'
                   },
                   body: JSON.stringify(data)
               });

               const result = await response.json();

               if (response.ok) {
                   mostrarModal(
                       "¡Guardado Correctamente!",
                       `<div class="text-center">
                           <p class="text-success fw-bold">${result.mensaje || 'Siniestro procesado'}</p>
                           <p>El expediente de <strong>${data.cliente.nombre}</strong> ya ha sido registrado.</p>
                        </div>`,
                       "bg-success text-white"
                   );
                   form.reset();
               } else {
                   throw new Error(result.error || "Error en el servidor");
               }
           } catch (error) {
               mostrarModal("Error de Envío", `<p class="text-danger">${error.message}</p>`, "bg-danger text-white");
           }
       }
   });

   // --- EVENTO: CONSULTA (GET) ---
   btnBuscar.addEventListener('click', async () => {
       const busqueda = document.getElementById('inputBusqueda').value.trim();
       if (!busqueda) return alert("Introduce un DNI o ID");

       const container = document.getElementById('infoResult');
       container.innerHTML = `<div class="text-center py-3"><div class="spinner-border text-primary"></div><p>Buscando...</p></div>`;
       container.style.display = 'block';

       try {
           // LLAMADA FETCH GET (Enviamos el parámetro de búsqueda en la URL)
           const response = await fetch(`${API_URL}consultar?search=${encodeURIComponent(busqueda)}`);
           const data = await response.json();

           if (response.ok) {
               visualizarInfo(data);
           } else {
               container.innerHTML = `<div class="alert alert-warning">No se encontró ningún expediente con ese ID/DNI.</div>`;
           }
       } catch (error) {
           container.innerHTML = `<div class="alert alert-danger">Error al conectar con la API: ${error.message}</div>`;
       }
   });

   // --- FUNCIONES DE APOYO ---
   function validarVacios() {
       const inputs = form.querySelectorAll('[required]');
       let valido = true;
       inputs.forEach(input => {
           if (!input.value.trim()) {
               input.classList.add('is-invalid'); 
               valido = false;
           } else {
               input.classList.remove('is-invalid');
           }
       });
       if (!valido) alert("Por favor, rellena todos los campos obligatorios.");
       return valido;
   }

   function validarFormatos() {
       const d = document.getElementById('dni').value;
       const e = document.getElementById('email').value;
       const m = document.getElementById('matricula').value;
       if (!regex.dni.test(d)) { alert("DNI inválido"); return false; }
       if (!regex.email.test(e)) { alert("Email inválido"); return false; }
       if (!regex.matricula.test(m)) { alert("Matrícula inválida"); return false; }
       return true;
   }

   function capturarDatos() {
       return {
           id_siniestro: document.getElementById('id_siniestro').value.trim() || null,
           cliente: { 
               nombre: document.getElementById('nombre').value.trim(),
               dni: document.getElementById('dni').value.trim(),
               email: document.getElementById('email').value.trim()
           },
           vehiculo: {
               matricula: document.getElementById('matricula').value.trim(),
               marca: document.getElementById('marca').value.trim(),
               modelo: document.getElementById('modelo').value.trim(),
               anio: parseInt(document.getElementById('anio').value) || 0
           },
           poliza: {
               tipo: document.getElementById('tipo_poliza').value,
               limite: parseFloat(document.getElementById('limite').value),
               franquicia: parseFloat(document.getElementById('franquicia').value || 0)
           },
           reparacion: {
               taller: document.getElementById('taller').value.trim(),
               mo: parseFloat(document.getElementById('mano_obra').value || 0),
               piezas: parseFloat(document.getElementById('piezas').value || 0)
           }
       };
   }

   function visualizarInfo(data) {
       const container = document.getElementById('infoResult');
       container.style.display = 'block';
       
       const mo = data.reparacion?.mo || 0;
       const piezas = data.reparacion?.piezas || 0;
       const total = data.total || (mo + piezas);
   
       // --- DOCUMENTO PDF ---
       let documentoHTML = `<p class="text-muted">No hay documento asociado.</p>`;
   
       if (data.url_documento) {
           documentoHTML = `
               <div class="mt-4">
                   <h6 class="fw-bold">Documento del Siniestro</h6>
   
                   <!-- Vista previa -->
                   <div class="ratio ratio-4x3 border rounded mb-2">
                       <iframe 
                           src="${data.url_documento}" 
                           title="Documento PDF"
                           loading="lazy">
                       </iframe>
                   </div>
   
                   <!-- Descarga -->
                   <a href="${data.url_documento}" 
                      class="btn btn-outline-primary btn-sm"
                      target="_blank"
                      download>
                       Descargar PDF
                   </a>
               </div>
           `;
       }
   
       container.innerHTML = `
           <div class="card border-primary shadow-sm">
               <div class="card-header bg-primary text-white text-center fw-bold">
                   Detalle del Expediente
               </div>
               <div class="card-body">
                   <p><strong>Siniestro ID:</strong> ${data.id_siniestro || 'N/A'}</p>
                   <p><strong>Cliente:</strong> ${data.cliente?.nombre || 'Desconocido'}</p>
                   <p><strong>DNI:</strong> ${data.cliente?.dni || 'N/A'}</p>
                   <p><strong>Taller:</strong> ${data.reparacion?.taller || 'No asignado'}</p>
   
                   <hr>
   
                   <table class="table table-sm table-borderless">
                       <tr>
                           <td>Mano de Obra</td>
                           <td class="text-end">${mo.toFixed(2)}€</td>
                       </tr>
                       <tr>
                           <td>Piezas / Material</td>
                           <td class="text-end">${piezas.toFixed(2)}€</td>
                       </tr>
                       <tr class="border-top fw-bold text-primary">
                           <td>TOTAL</td>
                           <td class="text-end">${total.toFixed(2)}€</td>
                       </tr>
                   </table>
   
                   ${documentoHTML}
               </div>
           </div>
       `;
   }

   function mostrarModal(titulo, cuerpo, claseHeader) {
       document.getElementById('modalTitle').innerText = titulo;
       document.getElementById('modalBody').innerHTML = cuerpo;
       document.getElementById('modalHeader').className = "modal-header " + claseHeader;
       mainModal.show();
   }

});

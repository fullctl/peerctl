(function($, $tc, $ctl) {

$ctl.application.Peerctl.TemplateEditor = $tc.extend(
  "TemplateEditor",
  {
    TemplateEditor : function() {
      this.Tool("email_templates");
      this.preview_timeout = new twentyc.util.SmartTimeout(()=>{},100);
    },

    init: function() {
      this.widget("list", ($e) => {
        const list = new twentyc.rest.List(this.template("template_list", $e.list_container));
        list.formatters.default = (val, data) => {
          if (val)
            return "(default)";
          return '';
        }

        return list;
      });

      this.widget("form", ($e) => {
        return new twentyc.rest.Form(this.template("form_template", $e.editor));
      });

      this.widget("select_type", ($e) => {
        return new $ctl.application.Peerctl.TemplateTypeSelect(this.$w.form.element.find('#type'));
      });

      this.preview_client = new twentyc.rest.Client(
        this.$w.form.element.find("#preview").data("api-preview-default")
      );

      if (
        !grainy.check(`verified.asn.${fullctl.peerctl.network.asn}.?`, "c") &&
        !grainy.check(`verified.asn.${fullctl.peerctl.network.asn}.?`, "u")
      ) {
        this.view_mode = true;

        this.jquery.find('.template-read-only-permission').removeClass('hidden');

        this.$e.editor_title.text("View template");
        this.$e.menu.find(`[data-element="button_new_${this.tag}"]`).hide();

        this.$w.form.element.find('a.btn.btn-secondary').hide();
        this.$w.form.element.find('button.btn.submit').hide();
        this.$w.form.element.find('input, textarea').prop('disabled', true);
        this.$w.select_type.disable();

        this.$w.list.element.find('.templates a .icon-edit').removeClass('icon-edit').addClass('icon-view');
      }

      $(this.$w.select_type.element).on("change", ()=>{
        let val = this.$w.select_type.element.val();

        if(!val) {
          return this.$w.form.element.find('#preview,#body').val("")
        }

        $.ajax({
          method:'get',
          url:'/tmpl/'+this.tag+'/'+val
        }).done((text)=> {
          this.$w.form.element.find('#body').val(text);
          this.preview();
        });
      });

      this.edit_mode = false;
      this.active_changes = false;
      this.$w.list.local_actions.edit_template = (template)=>{
        this.$w.form.fill(template);
        this.preview();
        if (this.view_mode) return

        this.$e.editor.removeClass("create");
        this.$w.form.form_action = template.id;
        this.$w.form.method = "put";
        this.$e.editor_title.text("Edit template");
        this.edit_mode = true;
        this.$w.form.element.find(":input:not(#preview)").on("input", (e) => {
          // might be out of edit mode when the listener fires
          if (this.edit_mode) {
            this.active_changes = true;
          }
        });
      };

      this.$w.list.load();

      const reset_form = () => {
        this.$e.editor.addClass("create");
        this.$w.form.form_action = "";
        this.$w.form.method = "post";
        this.$w.form.reset();
        this.$e.editor_title.text("Create new template");
        this.$w.form.element.find('#preview,#body').val("");
        this.edit_mode = false;
      }

      this.$e.menu.find(`[data-element="button_new_${this.tag}"]`).click(()=>{
        if (this.edit_mode && this.active_changes &&
          !confirm("You have unsaved edits, are you sure you want to discard them?")) {
          return;
        }
        reset_form();
        this.$w.form.element.find(":input").first().focus();
      });

      this.$w.form.element.find('a.btn.btn-secondary').click(()=>{
        reset_form()
      });

      $(this.$w.form).on("api-write:success", ()=>{
        this.active_changes = false;
        if (!this.edit_mode) {
          reset_form();
        }
        this.$w.list.load();
      });

      this.$w.form.element.find("#body").on("input", ()=>{
        this.preview();
      });

    },

    sync : function() {
      this.$w.list.load();
    },

    preview : function() {
      const type =this.$w.select_type.element.val();
      const preview_textarea = this.$w.form.element.find('#preview');
      const loading_shim = this.$w.form.element.find('.loading-shim');

      preview_textarea.prop("disabled", true).val("");
      loading_shim.show();

      this.preview_timeout.set(()=>{
        this.preview_client.post(null, {
          type: type,
          body: this.$w.form.payload().body,
          device: fullctl.peerctl.port_object().device.id
        }).then((response)=>{
          preview_textarea
            .val(response.first().body)
            .prop("disabled", false);
        }).finally(() => {
          loading_shim.hide();
        });
      },500);
    }
  },
  $ctl.application.Tool
);


$ctl.application.Peerctl.TemplateTypeSelect = $tc.extend(
  "TemplateTypeSelect",
  {
    TemplateTypeSelect : function(jq) {
      this.Select(jq);
    },

    done_processing : function() {
      if (this.is_disabled()) {
        return
      }

      this.Select_done_processing();
    },

    disable : function() {
      this.element.prop('disabled', true);
      this.disabled = true;
      this.element.find('option[value=""]').text('');
      this.load().then(()=> {
        this.element.find('option[value=""]').text('')
      });
    },

    is_disabled : function() {
      return this.disabled;
    }
  },
  twentyc.rest.Select
);


$ctl.application.Peerctl.EmailTemplates = $tc.extend(
  "EmailTemplates",
  {
    EmailTemplates : function() {
      this.tag = "email_template";
      this.Tool("email_templates");
      this.preview_timeout = new twentyc.util.SmartTimeout(()=>{},100);
    }
  },
  $ctl.application.Peerctl.TemplateEditor
);

$ctl.application.Peerctl.DeviceTemplates = $tc.extend(
  "DeviceTemplates",
  {
    DeviceTemplates : function() {
      this.tag = "device_template";
      this.Tool("device_templates");
      this.preview_timeout = new twentyc.util.SmartTimeout(()=>{},100);
    }
  },
  $ctl.application.Peerctl.TemplateEditor
);

$ctl.application.Peerctl.DeviceTemplateSelect = $tc.extend(
  "DeviceTemplateSelect",
  {
    load_params : function() {
      let port = fullctl.peerctl.port_object();
      if(port && port.device.type) {
        return {device_type: port.device.type};
      }
    }
  },
  twentyc.rest.Select
);

$ctl.application.Peerctl.EmailTemplateSelect = $tc.extend(
  "EmailTemplateSelect",
  {
    load_params : function() {
    }
  },
  twentyc.rest.Select
);

$($ctl).on("init_tools", (e, app) => {

  // init email templates tool
  app.tool("email_templates", ()=> {
    return new $ctl.application.Peerctl.EmailTemplates();
  });

  // init device templates tool
  app.tool("device_templates", ()=> {
    return new $ctl.application.Peerctl.DeviceTemplates();
  });

  app.$t.email_templates.activate();
  app.$t.device_templates.activate();

  $('#tab-summary-sessions').on('show.bs.tab', () => {
  });

});

})(jQuery, twentyc.cls, fullctl);
(function($, $tc, $ctl) {

$ctl.application.Peerctl.Networks = $tc.extend(
  "Networks",
  {

    Networks : function() {
      this.Tool("networks");
    },

    init : function() {

      this.select_network_search = $ctl.peerctl.$c.toolbar.$e.network_search_asn;

      this.select_network_search.select2({
        ajax: {
          url : '/autocomplete/pdb/net',
          dataType: 'json',
          processResults : function(data, params) {

            var term = params.term;
            if(!isNaN(parseInt(term))) {
              var exact_found = data.results.find((obj) => { return obj.id == parseInt(term) });
              if(!exact_found) {
                data.results.unshift({
                  id: parseInt(term),
                  text: "AS"+term,
                  selected_text: "AS"+term
                });
              }
            }
            console.log("DATA", data.results, exact_found);
            return {
              results: data.results
            }
          }
        },
        placeholder: "Search by ASN"
      });

      this.select_network_search.on('select2:select', (e)=> {
        this.sync();
      });

      $(document).on('select2:open', () => {
        document.querySelector('.select2-search__field').focus();
      });

      this.widget("list", ($e) => {
        return new $ctl.application.Peerctl.LocationList(
          this.template("list", this.$e.body)
        );
      })



      this.$w.list.element.find("[data-element=request_peering]").on("click", () => {
        this.request_peering();
      });

      this.request_peering_btn = new fullctl.application.DropdownBtn(this.$w.list.element.find(".dropdown-btn"));

    },

    sync : function() {
      if(this.select_network_search.val())
        this.$w.list.load(this.select_network_search.val());
    },

    request_peering : function(type) {

      if(!this.peer) {
        return alert("No network in results");
      }

      var selected = this.$w.list.element.find('input[type=checkbox]:checked').parent()
      var ix_ids = []

      selected.each(function() {
        ix_ids.push($(this).data("ix-id"));
      });

      new $peerctl.modals.RequestPeering(
        this.peer,
        this.peer_request_data,
        ix_ids,
      );
    }


  },
  $ctl.application.Tool
)

$ctl.application.Peerctl.LocationList = $tc.extend(
  "LocationList",
  {
    LocationList : function(jq) {
      this.List(jq);

      this.request_peering_row = jq.find('[data-element="request_peering_tr"]');

      this.formatters.row = this.format_row;

      $(this).on("load:after", (ev,response) => {
        let request_peering = this.element.find('[data-element=request_peering]');
        request_peering.show().prop("disabled", false).children('.label').hide().filter('.ok').show();

        this.element.find('input[type=checkbox]:not(.select-all)').on("change", (ev) => {
          if(this.get_number_of_selected_networks() > 0) {
            request_peering.prop("disabled", false)
            this.request_peering_row.show();
          } else {
            request_peering.prop("disabled", true)
            this.request_peering_row.hide();
          }
        });
      });

      $(this).on("api-read:success", (ev, endpoint, payload, response) => {

        if(!response.first()) {
          $('#network-search-result-name').text("");
          $('#network-search-result-asn').text("");
          this.peer = null;
          $('#searched-asn').text("");
          return;
        }

        this.peer = response.first();

        $('#network-search-result-name').text(this.peer.name);
        $('#network-search-result-asn').text(this.peer.asn);
        $('#searched-asn').text(this.peer.asn);

        this.peer_request_data = {type: "email"}
        // autopeer
        let url = `/api/autopeer/${fullctl.peerctl.network.asn}/enabled/${this.peer.asn}/`

        $.ajax({
          url: url,
          method: "GET",
          headers : {
            "Content-Type" : "application/json",
            "X-CSRFToken" : twentyc.rest.config.csrf
          },
        }).then((response)=>{
          const autopeer_data = this.autopeer_data = response.data[0];
          if (autopeer_data.enabled) {
            const autopeer_btn = $(`
                <button
                  class="primary btn | small active"
                  data-option-text="Autopeer"
                >
                  <div class="row align-items-center">
                    <div class="col label pe-0">
                      Request peering
                    </div>
                    <div class="col-auto">
                      <span class="icon icon-api"></span>
                    </div>
                  </div>
                </button>
            `)
            this.request_peering_btn.add_option(autopeer_btn);
            autopeer_btn.click(()=>{
              this.peer_request_data = {type: "autopeering", url: this.autopeer_data.url, autopeer_enabled: true, asn: this.peer.asn},
              this.request_peering();
            });

            this.$w.list.list_body.find('[data-element="request_peering"]').off('click')
            this.$w.list.element.find('[data-element="request_peering"]').on('click', ()=>{
              this.peer_request_data = {type: "email", url: this.autopeer_data.url, autopeer_enabled: true, asn: this.peer.asn};
              this.request_peering();
            });
          }
        });
      });

    },

    format_request_url : function(url) {
      return url.replace(/other_asn/, this.network_asn);
    },

    load : function(network_asn) {
      this.network_asn = network_asn;
      this.reset_request_peering_row();

      this.List_load();
    },

    get_number_of_selected_networks() {
      return this.element.find('input[type=checkbox]:checked').length;
    },

    format_row : function(row, data) {
        row.data("ix-id", data.ix_id);

        const cont_us = $('<div>');
        const cont_them = $('<div>');
        const cont_mutual = $('<div>');
        const session_icon = $('<img>').attr('src', fullctl.util.static('common/icons/Indicator/Check-Ind/Check.svg')).addClass("indicator").attr("title", "Peering session(s) configured")
        let loc, i, node;


        for(i=0; i< data.our_locations.length; i++) {
          loc = data.our_locations[i];
          const id = `${i}-our-location`;
          $('<div class="compact-row">').data("ix-id", loc.ix_id).append(
            $(`<input type="checkbox" id="${id}">`)
          ).append(
            $(`<label class="ms-1" for="${id}">`).text(loc.ix_name)
          ).appendTo(cont_us);
        }

        for(i=0; i< data.their_locations.length; i++) {
          loc = data.their_locations[i];
          const id = `${i}-their-location`;
          $('<div class="compact-row">').data("ix-id", loc.ix_id).append(
            $(`<input type="checkbox" id="${id}">`)
          ).append(
            $(`<label class="ms-1" for="${id}">`).text(loc.ix_name)
          ).appendTo(cont_them);
        }

        for(i=0; i< data.mutual_locations.length; i++) {
          loc = data.mutual_locations[i];
          const id = `${i}-mutual-location`;
          node = $('<div class="compact-row field">').data("ix-id", loc.ix_id).append(
            $(`<input type="checkbox" id="${id}">`)
          ).append(
            $(`<label class="ms-1" for="${id}">`).text(loc.ix_name).addClass((loc.session ? "session-active" : ""))
          ).appendTo(cont_mutual);

          if(loc.session) {
            node.append(session_icon.clone());
          }
        }

        row.find('.our-locations').append(cont_us);
        new $ctl.application.Peerctl.NetworksSelectAll(row.find('#our-locations-select-all'), cont_us);
        row.find('.their-locations').append(cont_them);
        new $ctl.application.Peerctl.NetworksSelectAll(row.find('#their-locations-select-all'), cont_them);
        row.find('.mutual-locations').append(cont_mutual);
        new $ctl.application.Peerctl.NetworksSelectAll(row.find('#mutual-locations-select-all'), cont_mutual);
    },

    reset_request_peering_row : function() {
      this.request_peering_row.hide();
    }
  },
  twentyc.rest.List
);

$ctl.application.Peerctl.NetworksSelectAll = $tc.define(
  "NetworksSelectAll",
  {
    NetworksSelectAll : function(jq, container) {
      this.element = jq;
      this.container = container;

      if (container.find('input[type=checkbox]').length == 0) {
        this.element.parent().hide();
        return
      }

      this.element.on("change", () => {
        if(this.element.is(":checked")) {
          this.select_all();
        } else {
          this.unselect_all();
        }
      });

      this.monitor_selects();
    },

    select_all : function() {
      this.container.find('input[type=checkbox]').prop("checked", true).trigger("change");
    },

    unselect_select_all : function() {
      this.element.prop("checked", false);
    },

    unselect_all : function() {
      this.container.find('input[type=checkbox]').prop("checked", false).trigger("change");
    },

    monitor_selects : function() {
      this.container.find('input[type=checkbox]').on("change", () => {
        if(this.container.find('input[type=checkbox]:checked').length !== this.container.find('input[type=checkbox]').length) {
          this.element.prop("checked", false);
        }
      });
    }
  }
);

$($ctl).on("init_tools", (e, app) => {
  // init networks tool
  app.tool("networks", () => {
    return new $ctl.application.Peerctl.Networks();
  });

  app.$t.networks.activate();

  $('#tab-summary-sessions').on('show.bs.tab', () => {
  });

});

})(jQuery, twentyc.cls, fullctl);
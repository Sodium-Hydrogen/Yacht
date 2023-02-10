<template lang="html">
  <div class="template-form component">
    <v-card>
      <!-- <v-fade-transition>
        <v-progress-linear
          indeterminate
          v-if="isLoading"
          color="primary"
          bottom
        />
      </v-fade-transition> -->
      <v-form>
        <div class="d-flex">
          <v-row>
            <v-col class="flex-grow-1 flex-shrink-0">
              <v-card-title
                v-if="this.composeTarget && !this.existing"
                class="mt-1"
              >
                New Compose Template
              </v-card-title>
              <v-card-title
                v-if="this.composeTarget && this.existing"
                class="mt-1"
              >
                Edit {{ this.projectName }} Project
              </v-card-title>
              <v-card-title v-if="!this.composeTarget" class="mt-1">
                Edit {{ this.projectName }} Env File: {{ form.name }}
              </v-card-title>
            </v-col>
            <v-col v-if="this.composeTarget" class="flex-grow-1 flex-shrink-0">
              <v-text-field
                v-if="!this.existing"
                class="mr-3"
                v-model="form.name"
                label="Template Name"
                required
              >
              </v-text-field>
            </v-col>
            <v-col class="text-right">
              <v-btn @click="submitFile()" class="mr-2 mt-3">
                submit
                <v-icon>mdi-content-save-outline</v-icon>
              </v-btn>
              <v-btn @click="closeEditor()" color="error" class="mr-2 mt-3">
                close
                <v-icon>mdi-close-circle-outline</v-icon>
              </v-btn>
            </v-col>
          </v-row>
        </div>
        <editor
          v-model="form.content"
          @init="editorInit"
          :lang="editorLang()"
          :theme="editorTheming()"
          :height="windowHeight"
          :width="windowWidth"
          class="editor"
          ref="braceEditor"
        ></editor>
      </v-form>
    </v-card>
    <v-dialog v-model="confirmDiscard" max-width="290">
      <v-card>
        <v-card-title class="headline" style="word-break: break-word;">
          You have unsaved changes.
        </v-card-title>
        <v-card-text>
          It looks like you have changed the open file. If you leave before
          saving, your changes will be lost.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="confirmDiscard = false">
            Keep Editing
          </v-btn>
          <v-btn text color="error" @click="confirmDiscardAction()">
            Discard
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script>
import { mapActions, mapMutations } from "vuex";
import axios from "axios";
export default {
  data() {
    return {
      composeTarget: true,
      confirmDiscard: false,
      existing: false,
      form: {
        name: "",
        content: null
      },
      projectName: "",
      windowHeight: window.innerHeight - 205,
      windowWidth: window.innerWidth - 80
    };
  },
  components: {
    editor: require("vue2-ace-editor")
  },
  methods: {
    ...mapMutations({
      setErr: "snackbar/setErr"
    }),
    ...mapActions({
      readProject: "projects/readProject",
      readProjectFile: "projects/readProjectFile"
    }),
    editorInit() {
      require("brace/mode/yaml");
      require("brace/mode/ini");
      require("brace/theme/twilight");
      require("brace/theme/textmate");
    },
    editorLang() {
      if (this.composeTarget) {
        return "yaml";
      }
      return "ini";
    },
    editorTheming() {
      if (this.$vuetify.theme.dark == false) {
        return "textmate";
      } else {
        return "twilight";
      }
    },
    submitFile() {
      var url = `/api/compose/${this.projectName}/edit`;
      if (!this.composeTarget) {
        url += `file/${encodeURIComponent(this.form.name)}`;
      }
      axios
        .post(url, this.form, {})
        .then(response => {
          this.$router.push({
            path: `/projects/${response.data.project || response.data.name}`
          });
        })
        .catch(err => {
          this.setErr(err);
        });
    },
    confirmDiscardAction() {
      if (this.projectName && this.projectName != "_") {
        this.$router.push({ path: `/projects/${this.projectName}` });
      } else {
        this.$router.push({ path: "/projects" });
      }
    },
    closeEditor() {
      let undoCounter = this.$refs.braceEditor.editor.session.$undoManager
        .dirtyCounter;
      if (undoCounter > 0) {
        this.confirmDiscard = true;
      } else if (this.projectName && this.projectName != "_") {
        this.$router.push({ path: `/projects/${this.projectName}` });
      } else {
        this.$router.push({ path: "/projects" });
      }
    },
    async populateForm() {
      this.projectName = this.$route.params.projectName;
      const envFile = this.$route.params.envFile;
      this.composeTarget = envFile === undefined;
      if (this.projectName != "_" && this.projectName != null) {
        var project;
        if (this.composeTarget) {
          project = await this.readProject(this.projectName);
        } else {
          project = await this.readProjectFile({
            Name: this.projectName,
            FileName: envFile
          });
        }
        this.form = {
          name: project.name || envFile || "",
          content: project.content || ""
        };
        this.existing = true;
      }
    }
  },
  async created() {
    await this.populateForm();
  }
};
</script>

<style lang="css">
.ace_gutter {
  z-index: 1;
}
.ace_gutter-active-line {
  z-index: 1;
}
.ace_editor {
  z-index: 1;
}
</style>

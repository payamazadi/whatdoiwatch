import { Component } from '@angular/core';
import axios from 'axios';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'Netflix Analyzer';
  data: any[] = [];
  loading: boolean = false;
  file: File | null = null;

  onFileChange(event: any) {
    this.file = event.target.files[0];
  }

  async onSubmit() {
    if(this.file?.type !== "text/csv") {
      alert("Please upload a CSV file.");
      return;
    }

    this.loading = true;

    try {
      const response = await axios.post('https://u7crgr0yuf.execute-api.us-east-1.amazonaws.com', this.file, {
        headers: {
          'Content-Type': 'application/octet-stream'
        },
      });

      this.data = response.data;
    } catch (error) {
      console.error("There was an error uploading the file.", error);
    }

    this.loading = false;
  }
}

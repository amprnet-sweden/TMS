/*
 * Copyright (C) 2026 AMPRnet Sverige
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 *  GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 */

package se.amprnet.tms.model;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.annotation.Nullable;
import org.springframework.http.HttpStatus;

public class ResultModel<T> {
    private final boolean status;
    private final ErrorModel error;
    private final T data;

    @JsonCreator
    public ResultModel(@JsonProperty("status") boolean status, @Nullable @JsonProperty("error") ErrorModel error, @Nullable @JsonProperty("data") T data) {
        this.status = status;
        this.error = error;
        this.data = data;
    }

    public ResultModel(T data) {
        this.status = true;
        this.error = null;
        this.data = data;
    }

    public ResultModel(ErrorModel error) {
        this.status = false;
        this.error = error;
        this.data = null;
    }

    public boolean isStatus() {
        return status;
    }

    public ErrorModel getError() {
        return error;
    }

    public T getData() {
        return data;
    }

    public static <T> ResultModel<T> success(T data) {
        return new ResultModel<>(data);
    }

    public static <T> ResultModel<T> error(HttpStatus status, String message) {
        return new ResultModel<>(new ErrorModel(status, message));
    }
}
